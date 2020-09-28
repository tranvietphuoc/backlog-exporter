import pandas as pd
from datetime import datetime
from utils import split_date, split_time
import numpy as np
import pytz


class Backlog:
    """Handle backlog."""

    shopee_codes = ["18692"]
    sendo_codes = ["1539", "1160902", "1160904", "1160905"]
    tiki_codes = ["1367"]
    lazada_codes = ["1041351", "9794"]
    tz = pytz.timezone("Asia/Ho_Chi_Minh")

    def __init__(self, export=None, inside=None, data=None):
        """Create dataframe"""
        self.df_export = pd.read_excel(export)
        self.df_inside = pd.read_excel(inside)

    def normalize(self):
        """Normalize data of dataframes."""
        # old names: new names
        name_replacement = {
            "Mã đơn": "MaDH",
            "Mã kiện": "MaKien",
            "Kho gửi": "KhoGui",
            "Kho nhận": "KhoNhan",
            "Kho hiện tại": "KhoHienTai",
            "TG đóng kiện": "TGDongKien",
            "TG cập nhật": "TGCapNhat",
            "TG nhận kiện": "TGNhanKien",
            "TG kết thúc": "TGKetThuc",
            "Trạng thái": "TrangThaiLuanChuyen",
            "Số đơn": "SoDon",
            "Khối lượng": "KhoiLuong",
            "Mã niêm phong đóng": "MaNiemPhongDong",
            "Mã niêm phong nhận": "MaNiemPhongNhan",
            "Hình thức đóng gói": "HinhThucDongGoi",
            "Hình thức vận chuyển": "HinhThucVanChuyen",
            "Ghi chú": "GhiChu",
        }

        # rename columns name of inside
        self.df_inside = self.df_inside.rename(columns=name_replacement)

        # normalize inside dataframe
        # datetime
        self.df_inside[
            [
                "TGDongKien",
                "TGCapNhat",
                "TGNhanKien",
                "TGKetThuc",
            ]
        ] = self.df_inside[
            [
                "TGDongKien",
                "TGCapNhat",
                "TGNhanKien",
                "TGKetThuc",
            ]
        ].apply(
            lambda x: pd.to_datetime(
                x, format="%d/%m/%Y %H:%M:%S"
            ).dt.tz_localize(tz=self.tz)
        )
        # convert type of int
        self.df_inside["KhoGui"] = self.df_inside["KhoGui"].astype(int)
        self.df_inside["KhoNhan"] = self.df_inside["KhoNhan"].astype(int)
        self.df_inside["KhoHienTai"] = self.df_inside["KhoHienTai"].astype(int)

        # normalize export dataframe
        # replace all <nil> to np.nan
        self.df_export = self.df_export.replace("<nil>", np.nan)

        # change str to datetime
        self.df_export[
            [
                "ThoiGianTao",
                "ThoiGianTaoChuyenDoi",
                "ThoiGianKetThucLay",
                "ThoiGianGiaoLanDau",
                "ThoiGianKetThucGiao",
                "ThoiGianGiaoHangMongMuon",
                "TGKetThucTra",
            ]
        ] = self.df_export[
            [
                "ThoiGianTao",
                "ThoiGianTaoChuyenDoi",
                "ThoiGianKetThucLay",
                "ThoiGianGiaoLanDau",
                "ThoiGianKetThucGiao",
                "ThoiGianGiaoHangMongMuon",
                "TGKetThucTra",
            ]
        ].apply(
            lambda x: pd.to_datetime(x).dt.tz_localize(tz=self.tz)
        )

        # join with inside dataframe
        self.data = pd.merge(
            self.df_export,
            self.df_inside[
                [
                    "MaDH",
                    "MaKien",
                    "KhoGui",
                    "KhoNhan",
                    "TGNhanKien",
                    "TrangThaiLuanChuyen",
                ]
            ],
            on="MaDH",
            how="left",
        )

    def calculate_backlog(self):
        """Classify and calculate all types of backlog."""

        # delivery backlog
        delivery_filter = (
            self.data["TrangThai"].isin(
                ["Đang giao hàng", "Giao hàng không thành công"]
            )
            | (
                (
                    (self.data["TrangThai"] == "Lưu kho")
                    | (self.data["TrangThai"] == "Lấy hàng thành công")
                    | (self.data["TrangThai"] == "Đang trung chuyển hàng")
                )
                & (self.data["KhoGiao"] == self.data["KhoHienTai"])
            )
            | (
                (self.data["TrangThai"] == "Chờ giao lại")
                & (
                    datetime.now(tz=self.tz) - self.data["ThoiGianKetThucGiao"]
                    > pd.Timedelta("24 hours")
                )
            )
        )
        delivery = self.data[delivery_filter]
        delivery["LoaiBacklog"] = "Kho giao"
        internal_delivery_filter = delivery["KhoLay"] == delivery["KhoHienTai"]
        delivery.loc[internal_delivery_filter, "N0"] = delivery.loc[
            internal_delivery_filter
        ]["ThoiGianKetThucLay"]
        delivery.loc[~internal_delivery_filter, "N0"] = delivery.loc[
            ~internal_delivery_filter
        ]["TGNhanKien"]
        delivery["N+"] = delivery["N0"] + pd.Timedelta(hours=120)
        delivery["Aging"] = (datetime.now(tz=self.tz) - delivery["N+"]).fillna(
            pd.Timedelta(hours=9999)
        )

        # returned backlog
        returned_filter = self.data["TrangThai"].isin(
            ["Đang hoàn hàng", "Hoàn hàng không thành công"]
        ) | (
            (
                (self.data["TrangThai"] == "Chuyển hoàn")
                | (self.data["TrangThai"] == "Đang trung chuyển hàng hoàn")
            )
            & (
                (
                    (~self.data["KhoTra"].isnull())
                    & (self.data["KhoTra"] == self.data["KhoHienTai"])
                )
                | (
                    (self.data["KhoTra"].isnull())
                    & (self.data["KhoLay"] == self.data["KhoHienTai"])
                )
            )
        )
        returned = self.data.loc[returned_filter]
        returned["LoaiBacklog"] = "Kho trả"
        internal_returned_filter = returned["KhoHienTai"] == returned["KhoGiao"]
        returned.loc[internal_returned_filter, "N0"] = returned.loc[
            internal_returned_filter
        ]["ThoiGianKetThucGiao"]
        returned.loc[~internal_returned_filter, "N0"] = returned.loc[
            ~internal_returned_filter
        ]["TGNhanKien"]
        returned["N+"] = returned["N0"] + pd.Timedelta(hours=72)
        returned["Aging"] = (datetime.now(tz=self.tz) - returned["N+"]).fillna(
            pd.Timedelta(hours=9999)
        )

        # pick up backlog
        pickup_filter = self.data["TrangThai"].isin(
            ["Chờ lấy hàng", "Đang lấy hàng", "Lấy hàng không thành công"]
        ) | (
            (self.data["TrangThai"] == "Tạo thành công")
            & (self.data["ThoiGianKetThucLay"].isnull())
        ) & (
            self.data["KhoHienTai"] == self.data["KhoLay"]
        )
        pickup = self.data[pickup_filter]
        pickup["LoaiBacklog"] = "Kho lấy"
        ecoms = (
            self.shopee_codes
            + self.sendo_codes
            + self.tiki_codes
            + self.lazada_codes
        )
        ecoms_filter = pickup["MaKH"].isin(ecoms)
        pickup.loc[ecoms_filter, "N0"] = pickup.loc[ecoms_filter][
            "ThoiGianTaoChuyenDoi"
        ]
        pickup.loc[~ecoms_filter, "N0"] = pickup.loc[~ecoms_filter][
            "ThoiGianTao"
        ]
        pickup["N+"] = pickup["N0"] + pd.Timedelta(hours=72)
        pickup["Aging"] = (datetime.now(tz=self.tz) - pickup["N+"]).fillna(
            pd.Timedelta(hours=9999)
        )

        # transporting backlog
        trans_filter = (
            (
                (self.data["TrangThai"] == "Lấy hàng thành công")
                | (self.data["TrangThai"] == "Lưu kho")
            )
            & (self.data["KhoGiao"] != self.data["KhoHienTai"])
        ) | (
            (self.data["TrangThai"] == "Đang trung chuyển hàng")
            & (self.data["KhoLay"] != self.data["KhoGiao"])
        )
        transporting = self.data.loc[trans_filter]
        transporting["LoaiBacklog"] = "Kho lấy luân chuyển"
        # spec_trans_filter = (transporting["DenTinh"] == "Hà Nội") | (
        #    transporting["DenTinh"] == "Hồ Chí Minh"
        # )
        transporting["N0"] = transporting["ThoiGianKetThucLay"]
        # transporting.loc[spec_trans_filter, "N+"] = transporting.loc[
        #    spec_trans_filter
        # ]["N0"] + pd.Timedelta(hours=12)
        # transporting.loc[~spec_trans_filter, "N+"] = transporting.loc[
        #    ~spec_trans_filter
        # ]["N0"] + pd.Timedelta(hours=32)
        transporting["N+"] = transporting["N0"] + pd.Timedelta(
            hours=12
        )  # HCM or HN deadline
        # transporting['N+'] = transporting['N0'] + pd.Timedelta(hours=32)  # all the rest
        # places
        transporting["Aging"] = (
            datetime.now(tz=self.tz) - transporting["N+"]
        ).fillna(pd.Timedelta(hours=9999))

        # return transporting backlog
        rt_filter = (
            self.data["TrangThai"].isin(["Chuyển hoàn", "Chờ chuyển hoàn"])
            | (self.data["TrangThai"] == "Đang trung chuyển hàng hoàn")
        ) & (
            (
                self.data["KhoTra"].isnull()
                & (self.data["KhoLay"] != self.data["KhoHienTai"])
            )
            | (
                ~self.data["KhoTra"].isnull()
                & (self.data["KhoTra"] != self.data["KhoHienTai"])
            )
        )
        return_transporting = self.data.loc[rt_filter]
        return_transporting["LoaiBacklog"] = "Kho giao luân chuyển"
        # spec_rt_filter = (return_transporting["TuTinh"] == "Hà Nội") | (
        #    return_transporting["TuTinh"] == "Hồ Chí Minh"
        # )
        return_transporting["N0"] = return_transporting["ThoiGianKetThucGiao"]
        # return_transporting.loc[spec_rt_filter, "N+"] = return_transporting.loc[
        #    spec_rt_filter
        # ]["N0"] + pd.Timedelta(hours=36)
        # return_transporting.loc[~spec_rt_filter, "N+"] = return_transporting.loc[
        #    ~spec_rt_filter
        # ]["N0"] + pd.Timedelta(hours=56)
        return_transporting["N+"] = return_transporting["N0"] + pd.Timedelta(
            hours=36
        )  # HCM or HN deadline
        # return_transporting['N+'] = return_transporting['N0'] + pd.Timedelta(hours=56)  # all the rest places
        return_transporting["Aging"] = (
            datetime.now(tz=self.tz) - return_transporting["N+"]
        ).fillna(pd.Timedelta(hours=9999))

        ecoms = (
            self.shopee_codes
            + self.sendo_codes
            + self.tiki_codes
            + self.lazada_codes
        )

        # composit data
        temp_data = delivery.append(
            [returned, pickup, transporting, return_transporting]
        )
        # ecommerces exchange
        temp_data["Ecommerces"] = "Others"
        # name of ecommerces exchange
        temp_data.loc[
            temp_data["MaKH"].isin(self.shopee_codes), "Ecommerces"
        ] = "Shopee"
        temp_data.loc[
            temp_data["MaKH"].isin(self.sendo_codes), "Ecommerces"
        ] = "Sendo"
        temp_data.loc[
            temp_data["MaKH"].isin(self.tiki_codes), "Ecommerces"
        ] = "Tiki"
        temp_data.loc[
            temp_data["MaKH"].isin(self.lazada_codes), "Ecommerces"
        ] = "Lazada"

        temp_data["Aging_ToanTrinh"] = np.nan
        ecoms_filter = temp_data["MaKH"].isin(ecoms)
        temp_data.loc[ecoms_filter, "Aging_ToanTrinh"] = (
            datetime.now(tz=self.tz)
            - temp_data[ecoms_filter]["ThoiGianTaoChuyenDoi"]
        )
        temp_data.loc[~ecoms_filter, "Aging_ToanTrinh"] = (
            datetime.now(tz=self.tz) - temp_data[~ecoms_filter]["ThoiGianTao"]
        )
        temp_data.reset_index(inplace=True)
        del temp_data["index"]
        temp_data["NgayHienTai"] = datetime.now(tz=self.tz).strftime("%Y-%m-%d")
        temp_data.drop_duplicates(inplace=True)
        # calculate the days of orders's aging
        temp_data["Days_Aging"] = (
            temp_data["Aging"].dt.round("d").apply(lambda x: x.days)
        )

        return temp_data

    def calculate_inventory(self):
        temp_data = self.calculate_backlog()
        inventory = temp_data.loc[
            (temp_data["LoaiBacklog"] == "Kho giao")
            & (temp_data["TrangThai"] != "Đang giao hàng")
        ]
        inventory["LoaiXuLy"] = "Chưa giao lại"
        never_delivery_filter = inventory["ThoiGianGiaoLanDau"].isnull()
        mistaken_delivery_filter = ~inventory["GhiChuGHN"].isnull() & inventory[
            "GhiChuGHN"
        ].str.contains(
            datetime.now(tz=pytz.timezone("Asia/Ho_Chi_Minh")).strftime(
                "%d/%m/%Y"
            )
        )
        inventory.loc[never_delivery_filter, "LoaiXuLy"] = "Chưa giao lần nào"
        inventory.loc[mistaken_delivery_filter, "LoaiXuLy"] = "Giao lỗi"

        inventory["N_ve_kho"] = inventory["N0"].apply(lambda x: split_date(x))
        inventory["H_ve_kho"] = inventory["N0"].apply(lambda x: split_time(x))

        del inventory["GhiChu"]
        return inventory


class Inventory(Backlog):
    def __init__(self, export=None, inside=None):
        super().__init__(export=export, inside=inside)

    def calculate_inventory(self):
        return super().calculate_inventory(self)
