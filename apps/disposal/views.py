import os
from datetime import datetime
from pathlib import Path

from flask import (Blueprint, redirect, render_template, request, session,
                   url_for)
from flask_paginate import Pagination, get_page_parameter
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas
from sqlalchemy import func

from apps.app import db
from apps.config import ITEM_CLASS_L, ITEM_CLASS_M, ITEM_CLASS_S
from apps.disposal.forms import GroceriesForm
from apps.register.models import Denomination, LostItem

disposal = Blueprint(
    "disposal",
    __name__,
    template_folder="templates",
    static_folder="static",
)

basedir = Path(__file__).parent.parent
UPLOAD_FOLDER = str(Path(basedir, "PDFfile", "disposal_file"))


# 保管物件情報一覧
@disposal.route("/dis_list", methods=["POST", "GET"])
def dis_list():
    form = GroceriesForm()
    search_dis = session.get('search_dislist', None)

    # ID情報が存在し、リストが空でない場合、それを使用してクエリを絞り込む
    if search_dis:
        start_date = search_dis['start_date']
        end_date = search_dis['end_date']
        item_feature = search_dis['item_feature']
        start_disposal_date = search_dis['start_disposal_date']
        end_disposal_date = search_dis['end_disposal_date']
        start_expiration_date = search_dis['start_expiration_date']
        end_expiration_date = search_dis['end_expiration_date']
        start_id = search_dis['start_id']
        end_id = search_dis['end_id']
        item_situation_sale = search_dis['item_situation_sale']
        item_situation_disposal = search_dis['item_situation_disposal']
        item_class_L = search_dis['item_class_L']
        item_class_M = search_dis['item_class_M']
        item_class_S = search_dis['item_class_S']

        # クエリの生成
        query = db.session.query(LostItem)
        if item_class_L != "選択してください":
            if item_class_L:
                item_class = item_class_L
                query = query.filter(LostItem.item_class_L == item_class)
            if item_class_M:
                item_class = item_class_M
                query = query.filter(LostItem.item_class_M == item_class)
            if item_class_S:
                item_class = item_class_S
                query = query.filter(LostItem.item_class_S == item_class)

        if start_date and end_date:
            query = query.filter(LostItem.get_item.between(start_date, end_date))
        elif start_date:
            query = query.filter(LostItem.get_item >= start_date)
        elif end_date:
            query = query.filter(func.date(LostItem.get_item) <= end_date)
        if item_feature:
            query = query.filter(LostItem.item_feature.ilike(f"%{item_feature}%"))
        if start_disposal_date and end_disposal_date:
            query = query.filter(LostItem.disposal_date.between(start_disposal_date,
                                                                end_disposal_date))
        elif start_disposal_date:
            query = query.filter(func.date(LostItem.disposal_date) >=
                                 start_disposal_date)
        elif end_disposal_date:
            query = query.filter(func.date(LostItem.disposal_date) <= end_disposal_date)
        if start_expiration_date and end_expiration_date:
            query = query.filter(LostItem.item_expiration.between(start_expiration_date,
                                                                  end_expiration_date))
        elif start_expiration_date:
            query = query.filter(func.date(LostItem.item_expiration) >=
                                 start_expiration_date)
        elif end_expiration_date:
            query = query.filter(func.date(LostItem.item_expiration) <=
                                 end_expiration_date)
        if start_id and end_id:
            query = query.filter(LostItem.main_id.between(start_id, end_id))
        elif start_id:
            query = query.filter(LostItem.main_id >= start_id)
        elif end_id:
            query = query.filter(LostItem.main_id <= end_id)
        if not item_situation_sale:
            query = query.filter(LostItem.item_situation != "売却済")
        if not item_situation_disposal:
            query = query.filter(LostItem.item_situation != "廃棄済")
        query = query.filter(LostItem.item_situation != "返還済み")
        search_results = query.all()
    else:
        # クエリの生成
        query = db.session.query(LostItem)
        query = query.filter(LostItem.item_situation != "売却済")
        query = query.filter(LostItem.item_situation != "廃棄済")
        query = query.filter(LostItem.item_situation != "返還済み")
        search_results = query.all()
    # ページネーション処理
    page = request.args.get(get_page_parameter(), type=int, default=1)
    rows = search_results[(page - 1)*50: page*50]
    pagination = Pagination(page=page, total=len(search_results), per_page=50,
                            css_framework='bootstrap5')

    if form.submit.data:
        # セッション情報として絞り込み条件
        session['search_dislist'] = {
            'start_date': form.start_date.data.strftime('%Y-%m-%d')
            if form.start_date.data else None,
            'end_date': form.end_date.data.strftime('%Y-%m-%d')
            if form.end_date.data else None,
            'item_feature': form.item_feature.data,
            'start_disposal_date': form.start_disposal_date.data.strftime('%Y-%m-%d')
            if form.start_disposal_date.data else None,
            'end_disposal_date': form.end_disposal_date.data.strftime('%Y-%m-%d')
            if form.end_disposal_date.data else None,
            'start_expiration_date': form.start_expiration_date.data.strftime
            ('%Y-%m-%d') if form.start_expiration_date.data else None,
            'end_expiration_date': form.end_expiration_date.data.strftime('%Y-%m-%d')
            if form.end_expiration_date.data else None,
            'start_id': form.start_id.data,
            'end_id': form.end_id.data,
            'item_situation_sale': form.item_situation_sale.data,
            'item_situation_disposal': form.item_situation_disposal.data,
            'item_class_L': request.form.get('item_class_L'),
            'item_class_M': request.form.get('item_class_M'),
            'item_class_S': request.form.get('item_class_S'),
        }
        return redirect(url_for("disposal.dis_list"))
    if form.submit_print.data:
        item_ids = request.form.getlist('item_ids')
        items = db.session.query(LostItem).filter(LostItem.id.in_(item_ids)).all()
        make_disposal_PDF(items)
        db.session.commit()
        return redirect(url_for('disposal.dis_list'))
    if form.submit_disposal.data:
        item_ids = request.form.getlist('item_ids')
        items = db.session.query(LostItem).filter(LostItem.id.in_(item_ids)).all()
        if form.disposal_date:
            for item in items:
                item.disposal_date = form.disposal_date.data
                item.item_situation = "廃棄済"
            db.session.commit()
        return redirect(url_for('disposal.dis_list'))
    if form.submit_register.data:
        item_ids = request.form.getlist('item_ids')
        items = db.session.query(LostItem).filter(LostItem.id.in_(item_ids)).all()
        if form.selling_date:
            for item in items:
                item.disposal_date = form.selling_date.data
                item.selling_price = form.selling_price.data
                item.item_situation = "売却済"
            db.session.commit()
        return redirect(url_for('disposal.dis_list'))
    return render_template("disposal/dis_list.html", form=form,
                           search_results=rows, pagination=pagination,
                           ITEM_CLASS_L=ITEM_CLASS_L,
                           ITEM_CLASS_M=ITEM_CLASS_M, ITEM_CLASS_S=ITEM_CLASS_S)


# PDFの作成
def make_disposal_PDF(items):
    current_time = datetime.now().strftime('%Y%m%d_%H%M%S')
    file_name = "disposal" + current_time + '.pdf'
    file_path = os.path.join(UPLOAD_FOLDER, file_name)
    p = canvas.Canvas(file_path, pagesize=landscape(A4))
    # ヘッダー部分(表までのテンプレ)
    p.setFont('HeiseiMin-W3', 20)
    p.drawString(350, 550, "還付済物件処理一覧")
    p.setFont('HeiseiMin-W3', 10)
    p.drawString(750, 520, datetime.now().strftime("%Y年%m月%d日"))

    # 表の部分
    p.rect(20, 480, 80, 20), p.rect(100, 480, 80, 20), p.rect(180, 480, 80, 20)
    p.rect(260, 480, 80, 20), p.rect(340, 480, 80, 20), p.rect(420, 480, 320, 20)
    p.rect(740, 480, 80, 20)
    p.drawCentredString(60, 485, "還付日"), p.drawCentredString(140, 485, "受理番号")
    p.drawCentredString(220, 485, "処理担当者"), p.drawCentredString(300, 485, "拾得日時")
    p.drawCentredString(380, 485, "金額"), p.drawCentredString(580, 485, "物件の種類及び特徴")
    p.drawCentredString(780, 485, "還付後処理")

    start_num = 450
    total_money = 0
    # 拾得物の内容記載
    for item in items:
        p.rect(20, start_num, 80, 30), p.rect(100, start_num, 80, 30)
        p.rect(180, start_num, 80, 30), p.rect(260, start_num, 80, 30)
        p.rect(340, start_num, 80, 30), p.rect(420, start_num, 320, 30)
        p.rect(740, start_num, 80, 30)

        denomination = Denomination.query.filter_by(lostitem_id=item.id).first()
        if item.refund_date:
            p.drawCentredString(60, start_num+10,
                                item.refund_date.strftime('%Y/%m/%d'))
        else:
            p.drawCentredString(60, start_num+10, "")
        p.drawCentredString(140, start_num+10, str(item.receiptnumber))
        if item.refund_manager:
            p.drawCentredString(220, start_num+10, item.refund_manager)
        if item.get_item:
            p.drawCentredString(300, start_num+10, item.get_item.strftime('%Y/%m/%d'))
        else:
            p.drawCentredString(300, start_num+10, "")
        if denomination is not None:
            p.drawCentredString(380, start_num+10, str(denomination.total_yen))
        p.drawCentredString(580, start_num+17, item.item_class_S)
        p.drawCentredString(580, start_num+5, item.item_feature)
        if item.refunded_process:
            p.drawCentredString(780, start_num+10, item.refunded_process)
        else:
            p.drawCentredString(780, start_num+10, "")
        if denomination is not None:
            total_money += denomination.total_yen
        start_num -= 30

    # 合計金額の記載
    p.drawString(580, start_num, "合計金額")
    p.drawString(625, start_num, str(total_money) + "円")
    p.line(580, start_num-3, 680, start_num-3)

    # Close the PDF object cleanly.
    p.showPage()
    p.save()

    return "making PDF"
