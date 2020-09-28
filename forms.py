from flask_wtf import FlaskForm
from wtforms import SubmitField
from flask_wtf.file import FileField, FileAllowed

from wtforms.validators import DataRequired


class UploadForm(FlaskForm):
    """Main page for application."""

    internal_file = FileField(
        "Upload file xuất từ export.ghn.dev tại đây.",
        validators=[DataRequired(), FileAllowed(["xlsx"])],
    )
    inside_file = FileField(
        "Upload file xuất từ inside.ghn.vn tại đây.",
        validators=[DataRequired(), FileAllowed(["xlsx"])],
    )
    submit = SubmitField("Upload")
