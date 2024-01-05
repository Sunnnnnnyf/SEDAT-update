
import requests

key = "4mYL7hGv3JIDYMx4dcPMggoRXceU7TrByFlXdsXo"
location = ["(-112.074011 33.448443)"]
for i in location:
    api = f'http://developer.nrel.gov/api/wind-toolkit/v2/wind/wtk-download.csv?api_key={key}&wkt=POINT{i}&names=2013&utc=false&leap_day=true&email=xf2241@columbia.edu'
    response = requests.get(api)
    filename = f"output_{i}.csv"  # 根据 index 生成不同的文件名，例如 output_0.csv、output_1.csv 等
    with open(filename, 'wb') as csv_file:
        csv_file.write(response.content)
#f'http://developer.nrel.gov/api/wind-toolkit/v2/wind/wtk-download.csv?api_key={key}&wkt=POINT{location}&names=2009&utc=true&leap_day=true&email=xf2241@columbia.edu'

          #f'api/wind-toolkit/v2/wind/wtk-download.csv?api_key={key}&wkt=POINT{i}&names=2009&utc=true&leap_day=true&email=zz2322@columbia.edu&reason=academic&affiliation=NREL'

    #data = requests.get(api)
    #csv_content = data.content
    #csv_file = open("output.csv",'wb')
    #csv_file.write(csv_content)
    print("done")

