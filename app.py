from flask import (
    Flask,
    redirect,
    render_template,
    url_for,
    make_response,
    session,
)
from forms import UploadForm
from core import Backlog
from flask_session import Session  # use to use session
from datetime import timedelta
import pandas as pd


app = Flask(__name__)

# config session for application
app.config["SESSION_TYPE"] = "filesystem"
app.config["SECRET_KEY"] = "secret"
app.config["SESSION_PERMANENT"] = True
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=6)
Session(app)


@app.route("/", methods=["GET", "POST"])
def index():
    """Handle data uploaded from form."""
    form = UploadForm()
    if form.validate_on_submit():
        b = Backlog(export=form.internal_file.data, inside=form.inside_file.data)
        b.normalize()  # normalize data
        temp = b.calculate_backlog()
        print(temp["Aging_ToanTrinh"])
        session["backlog"] = b.calculate_backlog().to_json(
            orient="records", date_format="iso"
        )
        session["inventory"] = b.calculate_inventory().to_json(
            orient="records", date_format="iso"
        )
        return redirect(url_for("export"))
    return render_template("index.html", form=form)


@app.route("/export", methods=["GET", "POST"])
def export():
    return render_template("export.html")


@app.route("/export/backlog", methods=["GET", "POST"])
def export_backlog():
    backlog = pd.read_json(
        session["backlog"],
    )
    backlog_to_export = backlog[
        [
            "NgayHienTai",
            "MaDH",
            "KhoLay",
            "KhoHienTai",
            "KhoGiao",
            "TrangThai",
            "GhiChuGHN",
            "SoLanLay",
            "SoLanGiao",
            "SoLanTra",
            "Ecommerces",
            "LoaiBacklog",
            "N0",
            "N+",
            "Aging",
            "Days_Aging",
            "Aging_ToanTrinh",
            "TrangThaiLuanChuyen",
            "MaKien",
        ]
    ]

    resp = make_response(
        backlog_to_export.to_csv(index=False, encoding="utf-8-sig")
    )  # make response of dataframe to csv
    resp.headers[
        "Content-Disposition"
    ] = "attachment; filename=backlog.csv"  # headers for file download
    resp.headers["Content-Type"] = "text/csv"
    return resp


@app.route("/export/inventory", methods=["GET", "POST"])
def export_inventory():
    inventory = pd.read_json(session["inventory"])
    inventory_to_export = inventory[
        [
            "NgayHienTai",
            "MaDH",
            "KhoLay",
            "KhoHienTai",
            "KhoGiao",
            "TrangThai",
            "GhiChuGHN",
            "SoLanGiao",
            "Ecommerces",
            "LoaiXuLy",
            "N_ve_kho",
            "H_ve_kho",
        ]
    ]

    resp = make_response(
        inventory_to_export.to_csv(index=False, encoding="utf-8-sig")
    )  # make response of dataframe to csv
    resp.headers[
        "Content-Disposition"
    ] = "attachment; filename=rp_giao.csv"  # headers for download
    resp.headers["Content-Type"] = "text/csv"
    return resp


if __name__ == "__main__":
    app.run(debug=True)
