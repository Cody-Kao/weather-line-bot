from flask import Flask, request, abort

import requests

import json

import datetime

from linebot import (
    WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import *

from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage
)   

import os

import re

if 'MPLCONFIGDIR' not in os.environ or os.environ['MPLCONFIGDIR'].startswith('/home'):
    import tempfile
    os.environ['MPLCONFIGDIR'] = tempfile.mkdtemp()

import matplotlib
matplotlib.use('Agg') 
import matplotlib.pyplot as plt
import io
import base64
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
matplotlib.rc('font', family='Microsoft JhengHei') # 讓matplotlib正確顯示中文

global user_position
user_position = {}

city_to_code = {"宜蘭縣":'F-D0047-001',"基隆市":'F-D0047-049',"台北市":'F-D0047-061',"新北市":'F-D0047-069',"桃園市":'F-D0047-005',"新竹市":'F-D0047-053',"新竹縣":'F-D0047-009',
          "苗栗縣":'F-D0047-013',"台中市":'F-D0047-073',"彰化縣":'F-D0047-017',"南投縣":'F-D0047-021',"雲林縣":'F-D0047-025',
          "嘉義市":'F-D0047-057',"嘉義縣":'F-D0047-029',"台南市":'F-D0047-077',"高雄市":'F-D0047-065',"屏東縣":'F-D0047-033',
          "花蓮縣":'F-D0047-041',"台東縣":'F-D0047-037',"澎湖縣":'F-D0047-045',"連江縣":'F-D0047-081',"金門縣":'F-D0047-085'}

authorization = os.environ.get('WEATHER_API_CODE')

query_dict = {'tem':'溫度', 'rainfall':'降雨機率'}

measure_dict = {'tem':"攝氏°C", 'rainfall':"機率%"} 

image_store = {}

def img_to_png(img):
    # Convert plot to PNG image
    pngImage = io.BytesIO()
    FigureCanvas(img).print_png(pngImage)
    
    # Encode PNG image to base64 string
    pngImageB64String = base64.b64encode(pngImage.getvalue()).decode('utf8')
    return pngImageB64String

def draw(file, query, city, region):
    # 針對所有字體進行修改
    font = {
        'weight' : 'bold',
        'size'   : 15}
    matplotlib.rc('font', **font)
    prefix = file['records']['locations'][0]['location']      
    y = []
    labels = []
    if query == 'tem':
        for reg in prefix:
            if reg['locationName'] == region:
                for description in reg['weatherElement'][0]['time']:
                    y.append(int(description['elementValue'][0]['value'].split('。')[2][-3:-1]))
                    labels.append(description['startTime'][-8:])
    elif query == 'rainfall':
        for reg in prefix:
            if reg['locationName'] == region:
                for description in reg['weatherElement'][0]['time']:
                    y.append(int(description['elementValue'][0]['value'].split('。')[1][-3:-1]))
                    labels.append(description['startTime'][-8:])
    date = prefix[0]['weatherElement'][0]['time'][0]['startTime'][:10]
    print('date: ', date)
    x = [i for i in range(len(y))]
    fig = plt.figure(figsize=(10.5,6))
    axis = fig.add_subplot(1, 1, 1)
    axis.set_title(city+'-'+region+'('+date+')')
    axis.set_xlabel("時間",fontsize=18)
    axis.set_ylabel(measure_dict[query], fontsize=18, rotation=0, loc='top')
    axis.set_ylim(0, 100) # 設定y軸的範圍
    axis.set_xticks(x, labels, fontsize=15)
    axis.grid()
    for i,j in zip(x,y):
        axis.annotate(str(j),xy=(i+0.05,j+0.05), ha='center', weight ='bold',fontsize=15) # 標記加上註記的點位，並對x y值做一些offset
    axis.plot(x, y, "o-", label=query_dict[query])
    plt.legend(
        loc='best',
        shadow=True,
        facecolor='#ccc',
        edgecolor='#000',
        title=query_dict[query],
        title_fontsize=20)
    return fig

def generate_image_and_link(tem_or_rainfall, city, region, today_or_tomorrow):
    if today_or_tomorrow:
        date = datetime.datetime.now().strftime('%Y-%m-%d')
    else:
        date = (datetime.datetime.now() + datetime.timedelta(1)).strftime('%Y-%m-%d')
    url = f'https://opendata.cwa.gov.tw/api/v1/rest/datastore/{city_to_code[city]}?Authorization={authorization}&format=JSON&elementName=WeatherDescription&timeFrom={date}T00%3A00%3A00&timeTo={date}T23%3A00%3A00'
    print("------------------url-----------------", url)
    req = requests.get(url)
    file = json.loads(req.content)

    if f"{date}{tem_or_rainfall}{city}{region}" not in image_store:
        img = draw(file, tem_or_rainfall, city, region)
        res = img_to_png(img)
    else:
        print("cache hits!")
        return image_store[f"{date}{tem_or_rainfall}{city}{region}"]

    headers = {"Authorization": "Client-ID 11c8e32c081b4ae"}

    url = "https://api.imgur.com/3/image"

    req = requests.post(
        url, 
        headers = headers,
        data = {  'image': res
        }
    )
    print(req.status_code)
    data = json.loads(req.text)['data']
    image_store[f"{date}{tem_or_rainfall}{city}{region}"] = data['link'] # save the url to the in-memory store
    print(data['link'])
    return data['link']

def getTemOrRain(file, query, city, region):
    prefix = file['records']['locations'][0]['location']      
    dataSet = []
    if query == 'tem':
        for reg in prefix:
            if reg['locationName'] == region:
                for description in reg['weatherElement'][0]['time']:
                    dataSet.append(int(description['elementValue'][0]['value'].split('。')[2][-3:-1]))
    elif query == 'rainfall':
        for reg in prefix:
            if reg['locationName'] == region:
                for description in reg['weatherElement'][0]['time']:
                    dataSet.append(int(description['elementValue'][0]['value'].split('。')[1][-3:-1]))
    date = prefix[0]['weatherElement'][0]['time'][0]['startTime'][:10]
    print('date: ', date)
    
    print(dataSet)
    delimitor = "=="*12
    if query == 'tem':
        return f"{date}\n{delimitor}最高溫: {max(dataSet)}°C\n平均溫度: {sum(dataSet)//len(dataSet)}°C\n最低溫度: {min(dataSet)}°C"
    elif query == 'rainfall':
        return f"{date}\n{delimitor}最高降雨機率: {max(dataSet)}%\n平均降雨機率: {sum(dataSet)//len(dataSet)}%\n最低降雨機率: {min(dataSet)}%"

def getData(tem_or_rainfall, city, region, today_or_tomorrow):
    if today_or_tomorrow:
        date = datetime.datetime.now().strftime('%Y-%m-%d')
    else:
        date = (datetime.datetime.now() + datetime.timedelta(1)).strftime('%Y-%m-%d')
        
    url = f'https://opendata.cwa.gov.tw/api/v1/rest/datastore/{city_to_code[city]}?Authorization={authorization}&format=JSON&elementName=WeatherDescription&timeFrom={date}T00%3A00%3A00&timeTo={date}T23%3A00%3A00'
    print("------------------url-----------------", url)
    req = requests.get(url)
    file = json.loads(req.content)
    data = getTemOrRain(file, tem_or_rainfall, city, region)
    
    return data

def get_pm25(user_city):
    user_city = user_city.replace('台', '臺')
    url = 'http://data.moenv.gov.tw/api/frontstage/datastore/search-result.download'
    data = {'resource_id': "d5fa0c88-b846-4362-9ed1-bf283aa52857", 'limit': 100, 'offset': 0, 'download_type': "json"}
    req = requests.post(url, data = data)
    file = json.loads(req.content)
    res = []
    for county in file:
        if county['county'] == user_city:
            res.append([county['site'], county['pm25']])
    
    res = sorted(res, key=lambda x:int(x[1]) if x[1] else 0, reverse=True)
    print(res)
    return (res[:4], county['datacreationdate']) # 取該地區前四筆是因為最多回復五則訊息 且有一筆保留給訊息標頭

app = Flask(__name__)

# 必須放上自己的Channel Access Token
configuration = Configuration(access_token=os.environ.get('channel_access_token')) # os.environ['channel_access_token']
# 必須放上自己的Channel Secret
handler = WebhookHandler(os.environ.get('channel_secret')) # os.environ['channel_secret']

#line_bot_api.push_message('U2ddc3390d5074b7f187a3e5518ed3480', TextSendMessage(text='你可以開始了')) # os.environ['user_id']

@app.route("/")
def home():
    return "Hello World"

# 監聽所有來自 /callback 的 Post Request
@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.info("Invalid signature. Please check your channel access token/channel secret.")
        abort(400)

    return 'OK'

 
#訊息傳遞區塊
##### 基本上程式編輯都在這個function #####
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    with ApiClient(configuration) as api_client:
        body = request.get_json()
        line_bot_api = MessagingApi(api_client)
        user_text = event.message.text
        emoji = [
                    {
                        "index": 9,
                        "productId": "5ac21184040ab15980c9b43a",
                        "emojiId": "007"
                    }
                ]      
        if re.match('當前綜合天氣彙報',user_text):
            if event.source.user_id in user_position:
                city, region = user_position[event.source.user_id]
                now = datetime.datetime.now()
                #now_plus_three_hours = now + datetime.timedelta(hours=3)
                url = f'https://opendata.cwa.gov.tw/api/v1/rest/datastore/{city_to_code[city]}?Authorization={authorization}&format=JSON&elementName=WeatherDescription&timeFrom={now.strftime('%Y-%m-%d')}T00%3A00%3A00&timeTo={now.strftime('%Y-%m-%d')}T23%3A00%3A00'
                print("=================url========================", url)
                req = requests.get(url)
                print("------------------------Code--------------------: ",req.status_code)
                file = json.loads(req.content)
                elements = file['records']['locations'][0]['location']

                for reg in elements:
                    if reg['locationName'] == region:
                        print(reg)
                        print("----------------------------")
                        print(reg['weatherElement'][0]['time'])
                        description = reg['weatherElement'][0]['time'][0]['elementValue'][0]['value'].split('。')
                        print('description: ', description)
                        tem = description[2][-3:-1]
                        rainfall = description[1][-3:-1]
                        wind = description[4][-4]
                        slogan = description[0]
                info = f"地區: {city}-{region}\n溫度: {tem}°C\n降雨機率: {rainfall}%\n風速: {wind}m/s\n天氣情況: {slogan}"
                print("--------------info--------------", info)
                message = TextMessage(text=info)
            else:
                message = TextMessage(text='請先設定使用者位置$', emojis=emoji)
        elif re.match('今明降雨機率',user_text):
            if event.source.user_id in user_position:
                user_address = user_position[event.source.user_id]
                today_data = getData('rainfall', user_address[0], user_address[1], 1)
                tomorrow_data = getData('rainfall', user_address[0], user_address[1], 0)
                textMsg = f"以下為{user_address[0]}{user_address[1]}之降雨機率\n\n{today_data}\n\n{tomorrow_data}"

                today_img_url = generate_image_and_link('rainfall', user_address[0], user_address[1], 1)
                tomorrow_img_url = generate_image_and_link('rainfall', user_address[0], user_address[1], 0)

                # 一個reply_token只能被使用一次! 所以一次就把所有訊息發完
        
                # Headers
                headers = {
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {os.environ.get('channel_access_token')}'
                }

                # Data payload
                data = {
                    'replyToken': event.reply_token,
                    'messages': [
                        {
                            "type":"text",
                            "text":textMsg
                        },
                        {
                            'type': 'image',
                            "originalContentUrl": today_img_url,
                            "previewImageUrl": today_img_url
                        },
                        {
                            'type': 'image',
                            "originalContentUrl": tomorrow_img_url,
                            "previewImageUrl": tomorrow_img_url
                        }
                    ]
                }

                # Send the POST request
                response = requests.post('https://api.line.me/v2/bot/message/reply', headers=headers, data=json.dumps(data))

                # Print the response
                print(response.status_code)
                print(response.json())

                return
            else: 
                message = TextMessage(text='請先設定使用者位置$', emojis=emoji)
        elif re.match('今明溫度',user_text):
            if event.source.user_id in user_position:
                user_address = user_position[event.source.user_id]
                today_data = getData('tem', user_address[0], user_address[1], 1)
                tomorrow_data = getData('tem', user_address[0], user_address[1], 0)
                textMsg = f"以下為{user_address[0]}{user_address[1]}之氣溫\n\n{today_data}\n\n{tomorrow_data}"
                
                today_img_url = generate_image_and_link('tem', user_address[0], user_address[1], 1)
                tomorrow_img_url = generate_image_and_link('tem', user_address[0], user_address[1], 0)

                # 一個reply_token只能被使用一次! 所以一次就把所有訊息發完
        
                # Headers
                headers = {
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {os.environ.get('channel_access_token')}'
                }

                # Data payload
                data = {
                    'replyToken': event.reply_token,
                    'messages': [
                        {
                            "type":"text",
                            "text":textMsg
                        },
                        {
                            'type': 'image',
                            "originalContentUrl": today_img_url,
                            "previewImageUrl": today_img_url
                        },
                        {
                            'type': 'image',
                            "originalContentUrl": tomorrow_img_url,
                            "previewImageUrl": tomorrow_img_url
                        }
                    ]
                }

                # Send the POST request
                response = requests.post('https://api.line.me/v2/bot/message/reply', headers=headers, data=json.dumps(data))

                # Print the response
                print(response.status_code)
                print(response.json())

                return

            else:  
                message = TextMessage(text='請先設定使用者位置$', emojis=emoji)
        elif re.match('當前pm2.5',user_text):
            if event.source.user_id in user_position:
                user_address = user_position[event.source.user_id]
                pm25, update_time = get_pm25(user_address[0])
                message = TextMessage(text=f'以下為{user_address[0]}當前pm2.5資訊\n資料更新時間為:\n{update_time}\n' + "\n" + "\n".join([f'[{site}]觀測站: {val}\n' for site, val in pm25]))
            else:
                message = TextMessage(text='請先設定使用者位置$', emojis=emoji)
        else:
            message = TextMessage(text=user_text)
        try:
            line_bot_api.reply_message_with_http_info(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[message]
                )
            )
            # Your code here
        except Exception as e:
            print(f"Error: {e}")
            raise  # Re-raise the exception to see the full traceback
        

@handler.add(MessageEvent, message=StickerMessage)
def handle_message(event):
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        message = 'Hello'
        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=message)]
            )
        )

@handler.add(MessageEvent, message=LocationMessage)
def handle_message(event):
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        complete_address = event.message.address.split("台灣")[1]
        address = ""
        for val in complete_address:
            address+= val
            if val == '區':
                break
        if event.source.user_id in user_position:
            if user_position[event.source.user_id] == [address[:3], address[3:]]:
                emoji = [
                    {
                        "index": 11,
                        "productId": "5ac1bfd5040ab15980c9b435",
                        "emojiId": "002"
                    }
                ]      
                message = TextMessage(text=f'親愛的你沒有移動過喔~$',emojis=emoji)
            else:
                user_position[event.source.user_id] = [address[:3], address[3:]]
                message = TextMessage(text=f'使用者位置已更改成:\n\U0001F449{address[:3]}-{address[3:]}\U0001F448')
        else:
            print(event.message.address)
            user_position[event.source.user_id] = [address[:3], address[3:]]
            message = TextMessage(text=f'使用者位置已設定為:\n\U0001F449{address[:3]}-{address[3:]}\U0001F448')
        
        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[message]
            )
        )
    
#主程式
if __name__ == "__main__":
    port = 5000
    app.run(host='0.0.0.0', port=port, debug=True) # Do not run the development server or debugger in a production environment. 會洩漏內部錯誤造成資安疑慮