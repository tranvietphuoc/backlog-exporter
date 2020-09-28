FROM python:3.8

RUN pip install flask pandas wtforms flask_wtf flask_session xlrd numpy gunicorn flask_babel pytz
RUN mkdir /app
ADD . /app
WORKDIR /app
RUN ls -la

CMD sh /app/run.sh
