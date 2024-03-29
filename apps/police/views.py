import os
from datetime import datetime
from pathlib import Path

from flask import Blueprint, redirect, render_template, request, session, url_for
from flask_paginate import Pagination, get_page_parameter
from reportlab.lib.pagesizes import A4, letter
from reportlab.pdfgen import canvas

from apps.app import db
from apps.police.forms import OptionDocument, PoliceForm, SubmitData
from apps.register.models import Denomination, LostItem

police = Blueprint(
    "police",
    __name__,
    template_folder="templates",
    static_folder="static",
)

basedir = Path(__file__).parent.parent
UPLOAD_FOLDER_OWNER = str(Path(basedir, "PDFfile", "police_file", "owner"))
UPLOAD_FOLDER_THIRD = str(Path(basedir, "PDFfile", "police_file", "third"))
UPLOAD_FOLDER_DISK = str(Path(basedir, "PDFfile", "police_file", "disk"))


# 警察届出
@police.route("/items", methods=["POST", "GET"])
def item():
    form = PoliceForm()
    search_results = session.get("search_polices", None)
    if search_results is None:
        query = db.session.query(LostItem)
        # 警察未届けの物のみ
        query = query.filter(LostItem.item_situation != "警察届出済み")
        query = query.filter(LostItem.item_situation != "返還済み")
        search_results = query.all()
    else:
        start_date = search_results["start_date"]
        end_date = search_results["end_date"]
        item_plice = search_results["item_plice"]
        item_finder = search_results["item_finder"]
        item_police = search_results["item_police"]
        item_return = search_results["item_return"]
        query = db.session.query(LostItem)
        if start_date and end_date:
            query = query.filter(LostItem.get_item.between(start_date, end_date))
        elif start_date:
            query = query.filter(LostItem.get_item >= start_date)
        elif end_date:
            query = query.filter(LostItem.get_item <= end_date)
        if item_plice is True:
            query = query.filter(LostItem.item_value is True)
        if item_finder != "すべて":
            if item_finder == "占有者拾得":
                query = query.filter(LostItem.choice_finder == "占有者拾得")
            else:
                query = query.filter(LostItem.choice_finder == "第三者拾得")
        if item_police is False:
            query = query.filter(LostItem.item_situation != "警察届出済み")
        if item_return is False:
            query = query.filter(LostItem.item_situation != "返還済み")

        search_results = query.all()

    # ページネーション処理
    page = request.args.get(get_page_parameter(), type=int, default=1)
    rows = search_results[(page - 1) * 50 : page * 50]
    pagination = Pagination(
        page=page, total=len(search_results), per_page=50, css_framework="bootstrap5"
    )

    if form.submit.data:
        # セッション情報として絞り込み条件
        session["search_polices"] = {
            "start_date": form.start_date.data.strftime("%Y-%m-%d")
            if form.start_date.data
            else None,
            "end_date": form.end_date.data.strftime("%Y-%m-%d")
            if form.end_date.data
            else None,
            "item_plice": form.item_plice.data,
            "item_finder": form.item_finder.data,
            "item_police": form.item_police.data,
            "item_return": form.item_return.data,
        }
        return redirect(url_for("police.item"))

    if form.submit_output.data:
        item_ids = request.form.getlist("item_ids")
        session["item_ids"] = item_ids
        return redirect(url_for("police.choice_document"))
    return render_template(
        "police/index.html", all_lostitem=rows, form=form, pagination=pagination
    )


# フレキシブルディスク提出票
@police.route("/submit_data", methods=["POST", "GET"])
def submit_data():
    form = SubmitData()
    if form.submit.data:
        info = form.info.data
        documents = form.documents.data
        make_submit_data(info, documents)
        return redirect(url_for("police.submit_data"))
    return render_template("police/submit_data.html", form=form)


def make_submit_data(info, documents):
    current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = "submit_data" + current_time + ".pdf"
    file_path = os.path.join(UPLOAD_FOLDER_DISK, file_name)
    p = canvas.Canvas(file_path, pagesize=A4)
    p.setFont("HeiseiMin-W3", 20)
    p.drawString(220, 800, "フレキシブルディスク提出票")
    p.setFont("HeiseiMin-W3", 10)
    p.drawString(20, 770, "遺失物法施行規則第26条の規定により提出すべき書類に記載することとされている事項を記録したフレキシブルディスクを")
    p.drawString(20, 760, "次のとおり提出します。")
    p.drawString(20, 750, "本票に添付されているフレキシブルディスクに記録された事項は、事実に相違ありません。")
    p.drawRightString(550, 730, datetime.now().strftime("%Y年%m月%d日"))
    p.drawString(200, 710, "殿")
    p.drawString(250, 670, "氏名又は名称")
    p.drawString(250, 650, "住所又は所在地")
    p.drawString(250, 620, "電話番号 その他連絡先")

    p.drawString(30, 500, "1 フレキシブルディスクに記載された事項")
    p.drawString(30, 490, info)
    p.drawString(30, 300, "2 フレキシブルディスクと併せて提出される書類")
    p.drawString(30, 290, documents)

    p.showPage()
    p.save()

    return "making PDF"


# 作成書類選択
@police.route("/choice/document", methods=["POST", "GET"])
def choice_document():
    form = OptionDocument()
    if form.submit.data:
        submit_date = form.submit_date.data
        if form.document.data == "占有者拾得物提出書":
            return redirect(url_for("police.make_data", submit_date=submit_date))
        else:
            return redirect(url_for("police.make_data_third", submit_date=submit_date))
    return render_template("police/choice_document.html", form=form)


# 警察届出用データ作成（占有者）
@police.route("/make/data", methods=["POST", "GET"])
def make_data():
    item_ids = session.get("item_ids", [])
    item_ids = [int(i) for i in item_ids]
    # Use in_ to filter rows where LostItem.id is in item_ids
    items = db.session.query(LostItem).filter(LostItem.id.in_(item_ids)).all()
    submit_date = request.args.get("submit_date")
    for item in items:
        if submit_date:
            item.police_date = datetime.strptime(submit_date, "%Y-%m-%d")
        else:
            item.police_date = datetime.now()
        item.item_situation = "警察届出済み"
    db.session.commit()
    submit_date = request.args.get("submit_date")
    make_pdf_police(items, submit_date)
    print(len(items))
    return redirect(url_for("police.item"))


# 警察届出用データ作成（第三者）
@police.route("/make/data/third", methods=["POST", "GET"])
def make_data_third():
    item_ids = session.get("item_ids", [])
    item_ids = [int(i) for i in item_ids]
    # Use in_ to filter rows where LostItem.id is in item_ids
    items = db.session.query(LostItem).filter(LostItem.id.in_(item_ids)).all()
    submit_date = request.args.get("submit_date")
    for item in items:
        if submit_date:
            item.police_date = datetime.strptime(submit_date, "%Y-%m-%d")
        else:
            item.police_date = datetime.now()
        item.item_situation = "警察届出済み"
    db.session.commit()
    make_pdf_police_third(items, submit_date)
    print(len(items))
    return redirect(url_for("police.item"))


# 警察届出用データ作成関数（占有者）
def make_pdf_police(items, submit_date):
    current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = "owner" + current_time + ".pdf"
    file_path = os.path.join(UPLOAD_FOLDER_OWNER, file_name)
    p = canvas.Canvas(file_path, pagesize=letter)
    # ヘッダー部分(表までのテンプレ)
    p.setFont("HeiseiMin-W3", 20)
    p.drawString(200, 750, "占有者拾得物　提出書")
    p.setFont("HeiseiMin-W3", 10)
    p.drawString(20, 710, "遺失物法第4条又は第13条の規定により、次の通り物件を提出します。")
    p.drawString(250, 690, "警察署長殿")
    if submit_date:
        date_obj = datetime.strptime(submit_date, "%Y-%m-%d")
        p.drawRightString(550, 690, date_obj.strftime("%Y年%m月%d日"))
    else:
        p.drawRightString(550, 690, datetime.now().strftime("%Y年%m月%d日"))
    p.drawString(250, 670, "氏名又は名称")
    p.drawString(250, 650, "住所又は所在地")
    p.drawString(250, 620, "電話番号　その他連絡先")

    # 表の部分
    p.rect(20, 590, 100, 20), p.drawString(30, 595, "受理番号"), p.rect(120, 590, 100, 20)
    p.rect(20, 550, 100, 40), p.drawString(30, 565, "拾得者の名称等")
    p.rect(120, 550, 300, 40)
    p.rect(420, 550, 50, 40), p.drawString(430, 565, "権利"), p.rect(470, 550, 80, 40)
    p.drawString(480, 575, "1. 有権"), p.drawString(480, 555, "2. 失権"),
    p.setFont("HeiseiMin-W3", 15)
    p.drawString(476, 573, "〇")
    p.setFont("HeiseiMin-W3", 10)

    # 拾得物
    p.rect(20, 530, 40, 20), p.rect(60, 530, 300, 20), p.rect(360, 530, 80, 20),
    p.rect(440, 530, 70, 20), p.rect(510, 530, 70, 20)
    p.drawString(30, 535, "番号"), p.drawString(70, 535, "物件の種類及び特徴"),
    p.drawString(365, 535, "拾得日時・場所"), p.drawString(450, 535, "交付日時")
    p.drawString(520, 535, "管理番号")
    start_num = 460
    cnt = 1
    # 6個の枠の準備
    for i in range(6):
        if i >= len(items):
            p.line(20, start_num, 580, start_num + 70)
        p.rect(20, start_num, 40, 70), p.rect(60, start_num + 30, 300, 40)
        p.rect(360, start_num + 30, 80, 40), p.rect(440, start_num + 30, 70, 40)
        p.rect(510, start_num + 30, 70, 40)
        p.drawString(40, start_num + 30, str(cnt))
        cnt += 1

        p.drawString(70, start_num + 17, "一万")
        p.drawString(70 + 42, start_num + 17, "五千")
        p.drawString(70 + 42 * 2, start_num + 17, "二千")
        p.drawString(73 + 42 * 3, start_num + 17, "千")
        p.drawString(70 + 42 * 4, start_num + 17, "五百")
        p.drawString(73 + 42 * 5, start_num + 17, "百")
        p.drawString(70 + 42 * 6, start_num + 17, "五十")
        p.drawString(73 + 42 * 7, start_num + 17, "十")
        p.drawString(73 + 42 * 8, start_num + 17, "五")
        p.drawString(73 + 42 * 9, start_num + 17, "一")
        p.drawString(500, start_num + 17, "合計金額")
        p.rect(480, start_num + 15, 100, 15), p.rect(480, start_num, 100, 15)
        num = 0
        for i in range(10):
            p.rect(60 + num, start_num + 15, 42, 15), p.rect(
                60 + num, start_num, 42, 15
            )
            num += 42
        start_num -= 70

    start_num = 460
    cnt = 0
    # 選択された拾得物の記入
    for item in items:
        denomination = Denomination.query.filter_by(lostitem_id=item.id).first()
        if denomination is not None:
            p.drawString(75, start_num + 3, str(denomination.ten_thousand_yen))
            p.drawString(75 + 42, start_num + 3, str(denomination.five_thousand_yen))
            p.drawString(75 + 42 * 2, start_num + 3, str(denomination.two_thousand_yen))
            p.drawString(75 + 42 * 3, start_num + 3, str(denomination.one_thousand_yen))
            p.drawString(75 + 42 * 4, start_num + 3, str(denomination.five_hundred_yen))
            p.drawString(75 + 42 * 5, start_num + 3, str(denomination.one_hundred_yen))
            p.drawString(75 + 42 * 6, start_num + 3, str(denomination.fifty_yen))
            p.drawString(75 + 42 * 7, start_num + 3, str(denomination.ten_yen))
            p.drawString(75 + 42 * 8, start_num + 3, str(denomination.five_yen))
            p.drawString(75 + 42 * 9, start_num + 3, str(denomination.one_yen))
            p.drawString(500, start_num + 3, str(denomination.total_yen))
        p.drawString(70, start_num + 55, item.item_class_S)
        p.drawString(70, start_num + 40, item.item_feature)
        if item.get_item:
            p.drawString(370, start_num + 55, item.get_item.strftime("%Y/%m/%d"))
        else:
            p.drawString(370, start_num + 55, "")
        p.drawString(370, start_num + 40, item.find_area)
        p.drawString(520, start_num + 55, str(item.main_id))
        start_num -= 70

    # 備考欄
    p.drawString(30, 60, "備考")
    p.rect(20, 20, 40, 90), p.rect(60, 20, 520, 90)
    p.drawString(70, 50, "権利放棄：報労金の放棄"), p.drawString(70, 30, "告知区分：同意する")

    # Close the PDF object cleanly.
    p.showPage()
    p.save()

    return "PDF receipt saved as " + file_name


# 警察届出用データ作成関数（第三者）
def make_pdf_police_third(items, submit_date):
    pages = 1
    for item in items:
        current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = str(pages) + "third" + current_time + ".pdf"
        file_path = os.path.join(UPLOAD_FOLDER_THIRD, file_name)
        p = canvas.Canvas(file_path, pagesize=letter)
        # ヘッダー部分(表までのテンプレ)
        p.setFont("HeiseiMin-W3", 20)
        p.drawString(200, 750, "第三者拾得物　提出書")
        p.setFont("HeiseiMin-W3", 10)
        p.drawString(20, 710, "遺失物法第4条又は第13条の規定により、次の通り物件を提出します。")
        p.drawString(250, 690, "警察署長殿")
        if submit_date:
            date_obj = datetime.strptime(submit_date, "%Y-%m-%d")
            p.drawRightString(550, 690, date_obj.strftime("%Y年%m月%d日"))
        else:
            p.drawRightString(550, 690, datetime.now().strftime("%Y年%m月%d日"))
        p.drawString(250, 670, "氏名又は名称")
        p.drawString(250, 650, "住所又は所在地")
        p.drawString(250, 620, "電話番号　その他連絡先")

        # 表の部分
        p.rect(20, 590, 100, 20), p.drawString(30, 595, "受理番号"),
        p.rect(120, 590, 100, 20)
        p.rect(20, 550, 100, 40), p.drawString(30, 565, "拾得者の名称等")
        p.rect(120, 550, 300, 40)
        p.rect(420, 550, 50, 40), p.drawString(430, 565, "権利"), p.rect(470, 550, 80, 40)
        p.drawString(480, 575, "1. 有権"), p.drawString(480, 555, "2. 失権"),
        p.setFont("HeiseiMin-W3", 15)
        p.drawString(476, 573, "〇")
        p.setFont("HeiseiMin-W3", 10)

        # 拾得物
        p.rect(20, 530, 40, 20), p.rect(60, 530, 300, 20), p.rect(360, 530, 80, 20),
        p.rect(440, 530, 70, 20), p.rect(510, 530, 70, 20)
        p.drawString(30, 535, "番号"), p.drawString(70, 535, "物件の種類及び特徴"),
        p.drawString(365, 535, "拾得日時・場所"), p.drawString(450, 535, "交付日時")
        p.drawString(520, 535, "管理番号")
        start_num = 460
        cnt = 1
        # 6個の枠の準備
        for i in range(6):
            if i >= 1:
                p.line(20, start_num, 580, start_num + 70)
            p.rect(20, start_num, 40, 70), p.rect(60, start_num + 30, 300, 40)
            p.rect(360, start_num + 30, 80, 40), p.rect(440, start_num + 30, 70, 40)
            p.rect(510, start_num + 30, 70, 40)
            p.drawString(40, start_num + 30, str(cnt))
            cnt += 1

            p.drawString(70, start_num + 17, "一万")
            p.drawString(70 + 42, start_num + 17, "五千")
            p.drawString(70 + 42 * 2, start_num + 17, "二千")
            p.drawString(73 + 42 * 3, start_num + 17, "千")
            p.drawString(70 + 42 * 4, start_num + 17, "五百")
            p.drawString(73 + 42 * 5, start_num + 17, "百")
            p.drawString(70 + 42 * 6, start_num + 17, "五十")
            p.drawString(73 + 42 * 7, start_num + 17, "十")
            p.drawString(73 + 42 * 8, start_num + 17, "五")
            p.drawString(73 + 42 * 9, start_num + 17, "一")
            p.drawString(500, start_num + 17, "合計金額")
            p.rect(480, start_num + 15, 100, 15), p.rect(480, start_num, 100, 15)
            num = 0
            for i in range(10):
                p.rect(60 + num, start_num + 15, 42, 15), p.rect(
                    60 + num, start_num, 42, 15
                )
                num += 42
            start_num -= 70

        start_num = 460
        cnt = 0
        # 選択された拾得物の記入
        denomination = Denomination.query.filter_by(lostitem_id=item.id).first()
        if denomination is not None:
            p.drawString(75, start_num + 3, str(denomination.ten_thousand_yen))
            p.drawString(75 + 42, start_num + 3, str(denomination.five_thousand_yen))
            p.drawString(75 + 42 * 2, start_num + 3, str(denomination.two_thousand_yen))
            p.drawString(75 + 42 * 3, start_num + 3, str(denomination.one_thousand_yen))
            p.drawString(75 + 42 * 4, start_num + 3, str(denomination.five_hundred_yen))
            p.drawString(75 + 42 * 5, start_num + 3, str(denomination.one_hundred_yen))
            p.drawString(75 + 42 * 6, start_num + 3, str(denomination.fifty_yen))
            p.drawString(75 + 42 * 7, start_num + 3, str(denomination.ten_yen))
            p.drawString(75 + 42 * 8, start_num + 3, str(denomination.five_yen))
            p.drawString(75 + 42 * 9, start_num + 3, str(denomination.one_yen))
            p.drawString(500, start_num + 3, str(denomination.total_yen))
        p.drawString(70, start_num + 55, item.item_class_S)
        p.drawString(70, start_num + 40, item.item_feature)
        if item.get_item:
            p.drawString(370, start_num + 55, item.get_item.strftime("%Y/%m/%d"))
        else:
            p.drawString(370, start_num + 55, "")
        p.drawString(370, start_num + 40, item.find_area)
        p.drawString(520, start_num + 55, str(item.main_id))
        start_num -= 70

        # 備考欄
        p.drawString(30, 60, "備考")
        p.rect(20, 20, 40, 90), p.rect(60, 20, 520, 90)
        p.drawString(70, 95, "氏名："), p.drawString(100, 95, item.finder_name)
        if item.finder_address:
            p.drawString(70, 80, "住所："), p.drawString(100, 80, item.finder_address)
        else:
            p.drawString(70, 80, "住所：不明")
        if item.finder_tel1:
            p.drawString(70, 65, "連絡先："), p.drawString(110, 65, item.finder_tel1)
        else:
            p.drawString(70, 65, "連絡先：不明")
        p.drawString(70, 50, "権利放棄：報労金の放棄"), p.drawString(70, 30, "告知区分：同意する")

        # Close the PDF object cleanly.
        p.showPage()
        p.save()
        pages += 1

    return "PDF receipt saved as "
