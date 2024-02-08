from flask import Flask, request, jsonify, send_file
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from bson.codec_options import CodecOptions
import logging
import io

app = Flask(__name__)

mongo_client = MongoClient("mongodb://chillwise01:TlP77MP0fpKcqo1fdFdeUXU3vvt17p4SO46ULbOpTeMxKG8jQEWkBOy271yyoTsxRNmqcpgUVIEvACDbJ7VTiw==@chillwise01.mongo.cosmos.azure.com:10255/?ssl=true&retrywrites=false&replicaSet=globaldb&maxIdleTimeMS=120000&appName=@chillwise01@")
db = mongo_client['Chill_Wise']
users = db['users']
devices = db['devices']
sku_sales = db['sku_sales']
imgs_data = db['imgs_data']

@app.route('/')
def landing_page():
    return "Hello ChillWise!"


@app.route('/login', methods=['POST'])
def login():
    username = request.json.get('username')
    password = request.json.get('password')
    user = users.find_one({'username': username})

    if user and check_password_hash(user['password'], password):
        return jsonify({"login": "success"}), 200
    else:
        return jsonify({"login": "failure"}), 401


@app.route('/device_status', methods=['GET'])
def get_device_status():
    devices_data = list(devices.find({}, {'_id': 0}))  # 查询所有设备状态，不返回_id字段
    return jsonify(devices_data), 200


@app.route('/search_device', methods=['GET'])
def search_device():
    device_id = request.args.get('device_id')
    device_data = devices.find_one({'device_id': device_id}, {'_id': 0})  # 根据设备ID查询
    if device_data:
        return jsonify(device_data), 200
    else:
        return jsonify({"error": "Device not found"}), 404


@app.route('/data_showcase/sales_linechart')
def sales_linechart():
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=14)
    total_sales_by_date = {}

    sales_records = db.sku_sales.find(
        {"date": {"$gte": start_date.strftime("%Y-%m-%d"), "$lt": end_date.strftime("%Y-%m-%d")}}
    )
    for record in sales_records:
        date = record['date']
        daily_total = sum(record.get('daily_sku_sales', {}).values())
        total_sales_by_date[date] = daily_total

    dates = sorted(total_sales_by_date.keys())
    sales = [total_sales_by_date[date] for date in dates]

    # 创建折线图
    if dates:
        fig, ax = plt.subplots()
        ax.plot(dates, sales)
        ax.set(title='14 Days Total Sales', xlabel='Date', ylabel='Total Sales')

        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight')
        buf.seek(0)
        return send_file(buf, mimetype='image/png')
    else:
        return jsonify({"error": "No data available for the line chart"}), 404





@app.route('/data_showcase/sales_piechart')
def sales_piechart():
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=7)
    sku_sales_data = {}

    sales_records = db.sku_sales.find(
        {"date": {"$gte": start_date.strftime("%Y-%m-%d"), "$lt": end_date.strftime("%Y-%m-%d")}}
    )
    for record in sales_records:
        for sku, sales in record.get('daily_sku_sales', {}).items():
            sku_sales_data[sku] = sku_sales_data.get(sku, 0) + sales

    if sku_sales_data:
        fig, ax = plt.subplots()
        ax.pie(sku_sales_data.values(), labels=sku_sales_data.keys(), autopct='%1.1f%%')
        ax.set(title='7 Days SKU Sales')

        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight')
        buf.seek(0)
        return send_file(buf, mimetype='image/png')
    else:
        return jsonify({"error": "No data available for the pie chart"}), 404


@app.route('/data_showcase/sku_sales', methods=['GET'])
def get_sku_sales_data():
    date = request.args.get('date')
    if date:
        result = db.sku_sales.find_one({"date": date}, {"_id": 0, "daily_sku_sales": 1})
        if result:
            return jsonify(result.get('daily_sku_sales', {})), 200
        else:
            return jsonify({"error": "No data found for the specified date"}), 404
    else:
        return jsonify({"error": "Date parameter is required"}), 400


@app.route('/push_update', methods=['POST'])
def push_update():
    update_content = request.json.get('update_content')
    device_ids = request.json.get('device_ids')

    if validate_update_content(update_content):
        send_updates_to_devices(device_ids, update_content)
        return jsonify({"status": "updates sent"}), 200
    else:
        return jsonify({"status": "invalid update content"}), 400




@app.route('/sales_map', methods=['GET'])
def get_sales_map_data():
    data_type = request.args.get('type', 'installation')  # 默认为装机量
    try:
        sales_map_data = query_sales_map_data(data_type)
        return jsonify(sales_map_data), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

def query_sales_map_data(data_type):
    if data_type == 'installation':
        return query_installation_data()
    elif data_type == 'sales':
        # 获取当前日期，并格式化为与数据库中的日期格式相同
        current_date = datetime.utcnow().strftime('%Y-%m-%d')
        return query_daily_sales_data(current_date)
    else:
        raise ValueError("Invalid data type")


def query_installation_data():
    # 查询装机量数据
    devices = db.devices.find({}, {"_id": 0, "location": 1})
    return [{"lat": device['location']['latitude'], "lng": device['location']['longitude']} for device in devices]


def query_daily_sales_data(date):
    # 查询特定日期的日销量数据
    sales_data = db.devices.find({"date": date}, {"_id": 0, "location": 1, "daily_total_sales": 1})
    return [{"lat": data['location']['latitude'], "lng": data['location']['longitude'], "sales": data['daily_total_sales']} for data in sales_data]


def validate_update_content(update_content):
    # 校验上传更新内容的合法性
    return True


def send_updates_to_devices(device_ids, update_content):
    # 向所选择的设备发送对应更新内容
    pass


@app.route('/device_info', methods=['GET'])
def get_device_info():
    device_id = request.args.get('device_id')
    if not device_id:
        return jsonify({"error": "Device ID is required"}), 400

    device_info = devices.find_one({"device_id": device_id}, {'_id': 0})
    if device_info:
        return jsonify(device_info), 200
    else:
        return jsonify({"error": "Device not found"}), 404

@app.route('/get_device_images', methods=['GET'])
def get_device_images():
    device_id = request.args.get('device_id')
    date = request.args.get('date')

    if not device_id or not date:
        return jsonify({"error": "Device ID and date are required"}), 400

    device_data = imgs_data.find_one({"device_id": device_id, "date": date}, {"_id": 0, "images": 1})
    if device_data:
        return jsonify(device_data.get('images', [])), 200
    else:
        return jsonify({"error": "Data not found"}), 404


if __name__ == '__main__':
    app.run(debug=False)
