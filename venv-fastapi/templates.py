html_view="""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>미세먼지 측정값</title>
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.7.1/dist/leaflet.css" />
        <script src="https://unpkg.com/leaflet@1.7.1/dist/leaflet.js"></script>
        <style>
            #map { height: 100vh; width: 100%; margin: 0; }
        </style>
    </head>
<body>
    <h1>미세먼지 측정값</h1>
    <div class="filter-box">
            <label style="font-weight: bold; margin-right: 5px;">⏰ 시간 선택:</label>
            <select id="time-selector" onchange="location.href='/?selected_time=' + this.value">
            __OPTIONS_GOES_HERE__
            </select>
    </div>
    <div id="map"></div>

    <script>
        var map = L.map('map').setView([37.5665, 126.9780], 11);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);
        
        var seoulGuCoordinates = {
            "강남구": [37.5172, 127.0473], "강동구": [37.5301, 127.1238], "강북구": [37.6396, 127.0257],
            "강서구": [37.5509, 126.8495], "관악구": [37.4784, 126.9516], "광진구": [37.5385, 127.0824],
            "구로구": [37.4954, 126.8874], "금천구": [37.4568, 126.8954], "노원구": [37.6542, 127.0568],
            "도봉구": [37.6688, 127.0471], "동작구": [37.5124, 126.9395], "마포구": [37.5636, 126.9087],
            "서대문구": [37.5791, 126.9368], "서초구": [37.4836, 127.0327], "성동구": [37.5633, 127.0371],
            "성북구": [37.5894, 127.0167], "송파구": [37.5145, 127.1066], "양천구": [37.5169, 126.8665],
            "영등포구": [37.5264, 126.8962], "용산구": [37.5326, 126.9904], "은평구": [37.6027, 126.9291],
            "종로구": [37.5729, 126.9796], "중구": [37.5636, 126.9976], "중랑구": [37.6065, 127.0927],
            "동대문구": [37.5744, 127.0397]
        };

        var dustValues = __DATA__;

        function getColor(value) {
            if (value <= 15) return "green";  // 10 이하면 초록색
            if (value <= 30) return "orange"; // 30 이하면 주황(노란)색
            if (value > 30)return "red"
            else return "gray";                     // 그보다 높으면 빨간색
        }


        dustValues.forEach(function(item) {
            L.circle(seoulGuCoordinates[item.location], {
                color: getColor(item.dustValue),       // 테두리 색상 지정
                fillColor: getColor(item.dustValue),   // 원 내부 채우기 색상 지정
                fillOpacity: 0.5,                  // 투명도 (0 ~ 1 사이)
                radius: 1500                       // 원의 크기 (반지름 미터 단위)
            })
            .addTo(map)
            .bindTooltip(item.location + " (" + item.dustValue + ")", {
                permanent: true,   // 마우스를 올리지 않아도 '항상' 글자가 보이게 고정합니다.
                direction: "right", // 동그라미 원의 '오른쪽 옆'에 글자를 배치합니다.
                offset: [10, 0]    // 원과 글자가 너무 붙지 않게 오른쪽으로 10픽셀 띄웁니다.
            });
        
        
        });
    </script>
</body>
    </html>
    """