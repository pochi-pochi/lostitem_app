from datetime import datetime

from apps.app import db


# 拾得物基本クラス
# UIの左上から右下方向の順番
class LostItem(db.Model):
    __tablename__ = "lost_item"
    id = db.Column(db.Integer, primary_key=True)
    choice_finder = db.Column(db.String)
    track_num = db.Column(db.Integer)
    notify = db.Column(db.Boolean, default=False)
    # 拾得日時
    get_item = db.Column(db.DateTime, default=datetime.now)
    get_item_hour = db.Column(db.String)
    get_item_minute = db.Column(db.String)
    # 受付日時
    recep_item = db.Column(db.DateTime, default=datetime.now)
    recep_item_hour = db.Column(db.String)
    recep_item_minute = db.Column(db.String)
    recep_manager = db.Column(db.String)

    # 拾得者情報等の管理
    find_area = db.Column(db.String)
    find_area_police = db.Column(db.String)
    own_waiver = db.Column(db.String)
    finder_name = db.Column(db.String)
    own_name_note = db.Column(db.String)
    finder_age = db.Column(db.Integer)
    finder_sex = db.Column(db.String)
    finder_post = db.Column(db.String)
    finder_tel1 = db.Column(db.String)
    finder_tel2 = db.Column(db.String)

    # 拾得物の詳細情報
    item_class_L = db.Column(db.String)
    item_class_M = db.Column(db.String)
    item_class_S = db.Column(db.String)
    item_value = db.Column(db.Boolean, default=False)
    item_feature = db.Column(db.String)
    item_color = db.Column(db.String)
    item_storage = db.Column(db.String, default="アリオ亀有")
    item_storage_place = db.Column(db.String)
    item_maker = db.Column(db.String)
    item_expiration = db.Column(db.DateTime)
    item_num = db.Column(db.Integer)
    item_unit = db.Column(db.String)
    item_plice = db.Column(db.String)
    item_money = db.Column(db.String)
    item_remarks = db.Column(db.String)
    item_situation = db.Column(db.Boolean, default=False)

    # 占有者用入力項目
    finder_class = db.Column(db.String)
    finder_affiliation = db.Column(db.String)

    # 第三者用入力項目
    thirdparty_waiver = db.Column(db.String)
    thirdparty_name_note = db.Column(db.String)