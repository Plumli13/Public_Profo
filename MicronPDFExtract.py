import os
import re
import pandas as pd
from pypdf import PdfReader

def getOrderInfo(PDFpath) :
    # PDFpath = (r"C:\Users\FBTWUser\Desktop\東京威力inbox\4516655515.pdf")  #多頁
    # PDFpath = (r"C:\Users\FBTWUser\Desktop\東京威力inbox\3501550290.pdf")
    # PDFpath = (r"C:\Users\FBTWUser\Desktop\東京威力inbox\4516479490.pdf") #tet跑到下一行
    # PDFpath = (r"C:\Users\FBTWUser\Desktop\東京威力inbox\3501456372.pdf") #第二筆跨頁
    # PDFpath = (r"C:\Users\FBTWUser\Desktop\東京威力inbox\3501552126.pdf")
    #new 202605 跨行
    # PDFpath = (r"C:\Users\FBTWUser\Desktop\東京威力inbox\pdf\4516721144.pdf")
    # PDFpath = (r"C:\Users\FBTWUser\Desktop\東京威力inbox\pdf\4516732118.pdf")

    # PDFpath = (r"C:\Users\FBTWUser\Desktop\東京威力inbox\pdf\3501565887.pdf") #正確的運送地址位置】範本如下~PO#3501565887
    # PDFpath = (r"C:\Users\FBTWUser\Desktop\東京威力inbox\pdf\4516705522.pdf") #運送地址跑位 &細目跨行問題：PO#4516705522 OK
    # PDFpath = (r"C:\Users\FBTWUser\Desktop\東京威力inbox\pdf\4516770227.pdf") #PO#4516770227_項次120 &160發現有跨頁&跨行又抓取不到
    # #start index問題改設0
    # PDFpath = (r"C:\Users\FBTWUser\Desktop\東京威力inbox\pdf\4516471449.pdf") #異動單漏單未抓取：PO# 4516471449 >OK
    # PDFpath = (r"C:\Users\FBTWUser\Desktop\東京威力inbox\pdf\4516778054.pdf") #0508今日執行RPA, PO# 4516778054_項次10 
    # #0511
    # PDFpath = (r"C:\Users\FBTWUser\Desktop\東京威力inbox\pdf\0511\3501568986.pdf") 
    # PDFpath = (r"C:\Users\FBTWUser\Desktop\東京威力inbox\pdf\0511\4516471449.pdf") #重複
    # PDFpath = (r"C:\Users\FBTWUser\Desktop\東京威力inbox\pdf\0511\4516534022.pdf") 
    # PDFpath = (r"C:\Users\FBTWUser\Desktop\東京威力inbox\pdf\0511\4516778054.pdf") 
    # PDFpath = (r"C:\Users\FBTWUser\Desktop\東京威力inbox\pdf\0511\4516782570.pdf") 
    # PDFpath = (r"C:\Users\FBTWUser\Desktop\東京威力inbox\pdf\0513\4516471449.pdf") 
    # PDFpath = (r"C:\Users\FBTWUser\Desktop\東京威力inbox\pdf\preuse\4516778054.pdf") 
    


    reader = PdfReader(PDFpath)  
    text = ""
    for page in reader.pages:
        text += page.extract_text()
    # print(text) 取得PDF文字

    text = text.replace("\xa0", " ")   # 清除不斷行空格
    sections = text.split("明細號碼")  # 用明細號碼切割成list
    sections_0 = sections[0]               # 取明細號碼之前的內容
    lines = sections_0.split("\n")         # 再按行分割 ['訂購單', '(新增)', '4516655515', '金額： ¥194,476 JPY',...

    # 取得單據號碼customerPO_No 3501501268 
    filename = os.path.basename(PDFpath)
    customerPO_No = os.path.splitext(filename)[0]     # 取得檔名[0]

    #初始化fab
    fab = micap = currency = orderType = generalNote = orderStatus=""
    bFab = False 
    for i, line in enumerate(lines):
        # 取得幣別 'JPY'     找「金額：」全形:
        if re.match(r'\s*金額：\s*', line):
            currency = line.strip().split(" ")[-1]

        #取得訂單類型 (SAP Document Type：|SAP PO Document Type：) 'YSTD'
        elif re.match(r'\s*(SAP Document Type：|SAP PO Document Type：)\s*' , line):
            orderType = line.strip().split(" ")[-1]  

        #micap 付款條件：	Current Month End +60 Days
        elif (m := re.match(r'\s*付款條件：\s*(.*)', line)):
            micap = m.group(1).strip().replace("計劃細目","").replace("運輸條款資訊","").replace("物料","")

        #取得交貨地點 fab 運送地址代碼:  TW03_MC01 
        elif (m := re.match(r'\s*運送地址代碼:\s*(.*)', line)):
            fab = m.group(1).strip()
            bFab = True

        # 取得orderStatus : '訂購單'下個lines[i+1]&符合 (新增)、(變更) 等括號格式，去掉空白
        elif re.match(r'\s*訂購單\s*', line) and (m := re.match(r'\(.*?\)', lines[i+1].strip())):
            orderStatus = m.group(0).replace(" ", "")

    # generalNote 自動找「備註」和「(聯絡|其他)資訊」的位置
    start= end = None
    for i, line in enumerate(lines):
        if "備註" in line and start is None: 
            start = i
        if re.search(r"(聯絡|其他)資訊", line):
            end = i
            break
    generalNote= ("").join(lines[start:end]).strip()


    ##以下開始找明細項目schedule_line
    index = 0
    customerPOLine = "" 
    customerItem = ""
    tetItem = ""
    qty = ""
    scheduleShipDate = ""
    price = ""
    updStatus = "" #改固定填空20260421
    processType = ""

    # 標記processType "type35ZCAP"      if"新增"in orderStatus "ZCAP"== orderType)
    if(re.match("^35.+",customerPO_No)):
        if("新增"in orderStatus):
            if("ZCAP"== orderType):
                processType = "type35ZCAP"
            else:
                processType = "type35"
        elif("已取消" in orderStatus):
            processType = "typeCancel35"
        else:
            if("ZCAP"== orderType):
                if("已變更" in orderStatus or "部分已開發票" in orderStatus):
                    processType = "typeChange35ZCAP"
                if("已部分接收" in orderStatus):
                    processType = "typeChange35ZCAP2"
            else:
                processType = "typeChange35"

    if(re.match("^45.+",customerPO_No)):
        if("新增" in orderStatus):
            if("ZCAP"== orderType):
                processType = "type45ZCAP"
            else:
                processType = "type45"
        elif("已取消" in orderStatus):
            processType = "typeCancel45"
        else:
            if("ZCAP"== orderType):
                if("已變更" in orderStatus or "部分已開發票" in orderStatus):
                    processType = "typeChange45ZCAP"
                if("已部分接收" in orderStatus):
                    processType = "typeChange45ZCAP2"
            else:
                processType = "typeChange45"

    df = pd.DataFrame(columns = ["generalNote","processType","orderStatus","customerPO_No","currency","orderType","fab","customerPOLine","customerItem","tetItem","qty","price","scheduleShipDate","updStatus", "micap"])

    for s in sections[1:]:  # sections[1:] 明細號碼之後的內容
        lines_detail = s.split("\n") #換行split list of str

        #202604明細號碼之後修復換行 def()->schedule_line
        schedule_line = format(lines_detail).replace("物料", "")  

        fields = schedule_line.split()  
        # ['30', '1', 'MT3M80-001923-11', '810-63416', '40.000', '(EA)', '2026年7月8日', '¥3,623', 'JPY', '¥144,920', 'JPY']
        
        #每次回圈前初始化
        tetItem= customerItem= qty= scheduleShipDate= price =customerPOLine= ''
        
        min_price_val = float('inf') # 初始化：設定一個極大的數值作為price比較對象

        for j, field in enumerate(fields):
            # 到貨日期 2026年7月8日
            if (scheduleShipDate=="") and (m := re.match(r"^(\d{4}年\d{1,2}月\d{1,2}日)$", field)):
                scheduleShipDate = m.group(1)
            
            # 部件號 MT3M80-001923-11 或 TF開頭 
            elif (tetItem == '') and (m := re.match(r"(\w{5,7}\-\w{6}-[\w\(\)]{1,5}|TF\w{3,6}\-\w{3,6})", field)):
                tetItem = m.group(1)

            # 數量：取 (EA) 前一個 field 40.000
            elif (qty == '') and re.match(r"^\(\w+\)$", field):
                qty  = fields[j-1]   
            
            # 客戶零件號碼 810-63416
            # elif (customerItem =="") and (m := re.match(r"^(\d+\-\d+)$", field)):
            elif (customerItem =="") and (m := re.match(r"^(\d{3,5}\-\d{5,7})$", field)):
                customerItem = m.group(1)
            
            # 單價price ¥3,623.3 and price == ''取第一次 比較取小的
            elif (m := re.match(r"^(¥|\$|NT\$|€|£)([\d,]+\.?\d*)$", field)) :
                # price = m.group(1) + m.group(2)  
                # 比較取小的 轉為浮點數
                current_val = float(m.group(2).replace(',', ''))
                if current_val < min_price_val:
                    min_price_val = current_val
                    price = m.group(1) + m.group(2)  

            # 明細行號第一個純數字 10
            elif (customerPOLine == '') and (m := re.match(r"^\d+$", field)):
                customerPOLine = m.group(0)
            
            #bFab is False 前面沒找到 取得交貨地點 fab 運送地址代碼：  TW03_MC01 
            elif bFab is False and re.match(r'\s*運送地址代碼：\s*', field):
                fab = fields[j+1]
                                                
        df.loc[index] = [generalNote,processType,orderStatus,customerPO_No,currency,orderType,fab,customerPOLine,customerItem,tetItem,qty,price,scheduleShipDate,updStatus,micap]
        index = index + 1
    
    # #本機df.to_excel結果
    # p = PDFpath.replace("\\", "/").split("/")# → [..., '0511', '4516782570.pdf']
    # ExcelName = p[-2] + "_" + os.path.splitext(p[-1])[0]
    # df.to_excel(rf"C:\Users\FBTWUser\Desktop\東京威力inbox\pdf\output\{ExcelName}.xlsx", index=False)
    print(df)
    print(df.to_json(orient="records"))
    return df.to_json(orient="records")   


def format(data_list): 
    """找到 明細號碼之後 的list Join成字串 修復跨行
    目標 '10 1 MT023-003103-1   810-117816  9.000 (EA) 2026年7月7日 ¥3,188 JPY ¥28,692 JPY'"""

    clean_list = [str(s).strip() for s in data_list]
    start_index = 0 #start_pattern 可能找無
    end_index = -1
    
    end_pattern = re.compile(r'電話|交付日期|其他資訊') #r'狀態|計劃細目|其他資訊
    for i, text in enumerate(clean_list):
        if end_pattern.search(text):
            end_index = i
            break
        else : end_index = len(clean_list)
            
    # 找到切片並 Join列表元素合併成字串 #re.sub 直接修復字串中的斷行空格
    if  end_index != -1:
        target_sub_list = clean_list[start_index:end_index]
        result_string = " ".join(target_sub_list)

        # 20260507 定義修復規則清單：(正則模式, 替換目標)
        rules = [
            # 1. 修復部件號 (ES2L80- 001319-11, SR3B...- 11) \w{5,7}\-\w{6}-[\w\(\)]{1,5}
            (r"(\w{5,7}\-)\s+([\w-]+)", r"\1\2"),

            # 2. 修復客戶零件號 (810- 119949)
            (r"(\d{3,}\-)\s+(\d{3,})", r"\1\2"),
            
            # 3. 修復日期 (2026年6月 15日, 2026年10月21 日)
            # (r"(\d{4}年\d{1,2}月\d{0,2})\s+(\d{1,2}日|日)", r"\1\2"),
            (r"(\d{4}年\d{1,2}月\d{0,2})(.*?)(\d{1,2}日|日)", r"\1\3\2"), # 2026年6月 ..... 15日
            
            # 4. 移除剩餘不必要的中文標籤 (如：物料10 -> 10)
            (r"物料(\d+)", r"\1")
        ]
        for pattern, replacement in rules:
            result_string = re.sub(pattern, replacement, result_string)

        #552.pdf 如果不能整理出TET 針對「部件號重組」
        TetItem_pattern = r"(\w{5,7}-\w{6}-[\w()]{1,5} |TF\w{3,6}-\w{3,6})" #與前面相同正則參考
        if not re.search(TetItem_pattern, result_string):
                
            rules2 = [
                #--552.pdf FAB 跑位
                #490: ES2L05-810-      2.000 (EA) 2026年6月 ¥297,316 JPY MC01 運送地址 物 料 計劃細目 物 料 250470-11 135543 15日
                #990 1 DS028-011825-810-      9.000 (EA) 2026年6月 ¥560 JPY ¥5,040 JPY MC01 運送地址 物 料 計劃細目 物 料 1 90360 15日 
                # "810- "前插入%RPA%錨點 (使用非貪婪匹配定位最後一個橫槓)
                (r"(\w{6}-|w{5,7}-\w{6}-)(\d{3}- )", r"\1%RPA%\2"),
                #錨點 1 90360 & 250470-11 135543
                (r"(\w{6}-\w{2}|\d{1})\s+(\d{4,7})\b", r"\1%RPA%\2 "), #新增 (\d{4,7})\b 加上字元邊界 確保不抓到日期

                # 320 : "MT012-3QRA110-M5-C3H-3 CKD 810- "     (810- ).strip""
                (r"(\w{5,7}-)(.*) (\d{3}- )", r"\1%RPA%\3".strip(" ")),
                 #320 1 MT012-%RPA%810-      12.000 2026年6月15日 ¥11,109 JPY ¥133,308 JPY MC08 運送地址 物 料 計劃細目 物 料 014143-1%RPA%110846  (EA) 
                (r"(\d{4}年\d{1,2}月\d{1,2}日)(.*)(\(\w+\))", r"\3 \1 \2"), #320 修復(EA) 在日期前

                #227.pdf NO:160 "MTAS10-500058-810-167339 " ...計劃細目 11
                (r"(\w{5,7}-\w{6}-)(\d{3}-\d{5,6} )(.*)計劃細目 (\d+)",r"\1\4 \2 \3"),

                #最後重組490 &990 \1: ES2L05- | \2: 810- | \4: 250470-11 | \5: 135543
                (r"(.*)%RPA%(.*?)\s+(.*?)\s+([\w-]+)%RPA%(\d+)", r"\1\4 \2\5 \3")
            ]
            for pattern, replacement in rules2:
                result_string = re.sub(pattern, replacement, result_string)  
            result_string.replace("%RPA%"," ")
   
    return result_string

# getOrderInfo("")  #for uipath close this




# # testPDF = [
# #     r"C:\Users\FBTWUser\Desktop\東京威力inbox\pdf\3501565887.pdf",   # 正確的運送地址位置 PO#3501565887
# #     r"C:\Users\FBTWUser\Desktop\東京威力inbox\pdf\4516705522.pdf",   # 運送地址跑位 & 細目跨行 PO#4516705522
# #     r"C:\Users\FBTWUser\Desktop\東京威力inbox\pdf\4516770227.pdf",   # PO#4516770227 項次120&160 跨頁跨行
# #     r"C:\Users\FBTWUser\Desktop\東京威力inbox\pdf\4516471449.pdf",   # 異動單漏單 PO#4516471449
# #     r"C:\Users\FBTWUser\Desktop\東京威力inbox\pdf\4516778054.pdf",   # PO#4516778054 項次10
# #     # 0511
# #     r"C:\Users\FBTWUser\Desktop\東京威力inbox\pdf\0511\3501568986.pdf",
# #     r"C:\Users\FBTWUser\Desktop\東京威力inbox\pdf\0511\4516471449.pdf",
# #     r"C:\Users\FBTWUser\Desktop\東京威力inbox\pdf\0511\4516534022.pdf",
# #     r"C:\Users\FBTWUser\Desktop\東京威力inbox\pdf\0511\4516778054.pdf",
# #     r"C:\Users\FBTWUser\Desktop\東京威力inbox\pdf\0511\4516782570.pdf",
# # ]

# # for s in testPDF:
# #     getOrderInfo(s)
