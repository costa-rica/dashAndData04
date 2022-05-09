from flask import Blueprint
from flask import render_template, url_for, redirect, flash, request, abort, session,\
    Response, current_app, send_from_directory

import os
from datetime import datetime, date, time
import pandas as pd
from app_package.datatools.security.utils import uploadToDfUtil, \
    textToDfUtil, getStsUtil,toExcelUtility,makeDfUtil

import logging
from app_package.utils import logs_dir


#Setting up Logger
formatter = logging.Formatter('%(asctime)s:%(name)s:%(message)s')
formatter_terminal = logging.Formatter('%(asctime)s:%(filename)s:%(name)s:%(message)s')

logger_security = logging.getLogger(__name__)
logger_security.setLevel(logging.DEBUG)
logger_terminal = logging.getLogger('terminal logger')
logger_terminal.setLevel(logging.DEBUG)

file_handler = logging.FileHandler(os.path.join(logs_dir,'getSts.log'))
file_handler.setFormatter(formatter)

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter_terminal)

logger_security.addHandler(file_handler)
logger_terminal.addHandler(stream_handler)

#End set up logger


datatools_security = Blueprint('datatools_security', __name__)

 
# @datatools_security.route("/", methods=['POST','GET'])
@datatools_security.route("/getSTS", methods=['POST','GET'])
def getSTS():
    siteTitle = "Get STS Codes"
    # today = date.today().strftime("%m/%d/%Y")
    
    # DON'T DELETE - what is this for??????
    # if request.args.get('goToPriceIndices'):
    #     return redirect(url_for('datatools.priceIndices', goTo=request.args.get('goToPriceIndices')))
    
    get_sts_files_path = os.path.join(current_app.config['STATIC_PATH'],'utility_getSts')
    if not os.path.exists(get_sts_files_path):
        os.makedirs(get_sts_files_path)

    if request.method=="POST":
        logger_security.info(f'Security/getSTS POST request made')
        formDict = request.form.to_dict()
        filesDict = request.files.to_dict()
        
        uploadFilename = filesDict.get('uploadedFile').filename
        uploadedText = formDict.get('textareaEntry')
        
        #check file data upload type
        #make df from data upload
        if uploadFilename:
            uploadedFile = request.files['uploadedFile']
            if '.' in uploadFilename and uploadFilename.rsplit('.', 1)[1].lower() in ['xlsx', 'csv']:
                uploadDf=uploadToDfUtil(uploadFilename, uploadedFile)
            else:
                flash(f'File not accepted ', 'warning')
                return redirect(url_for('datatools.getSTS'))
        elif uploadedText:
            uploadDf=textToDfUtil(uploadedText)
        else:
            flash(f'No web addresses provided. Enter url in text box or upload spreadsheet', 'warning')
            return redirect(url_for('datatools.getSTS'))
        
        makeDfUtil(uploadDf)
            
        if formDict.get('button') == 'makeTable':
            stsTable = pd.read_excel(os.path.join(get_sts_files_path, 'STS Codes Report.xlsx'))
            print('stsTable:::')
            print(stsTable.dtypes)
            print(stsTable)
            # stsTable['Date']=stsTable['Date'].dt.date
            # stsTable['Date']=pd.to_datetime(stsTable['Date'])
            # stsTable['Date']=stsTable['Date'].astype('datetime64[ns]')
            stsTableColumns = stsTable.columns
            stsTable=stsTable.to_dict('records')
            return render_template("datatools/getSts.html", siteTitle = siteTitle,stsTable=stsTable, stsTableColumns=stsTableColumns, len=len)       

        elif formDict.get('button') == 'downloadTable':
            return send_from_directory(get_sts_files_path,'STS Codes Report.xlsx', as_attachment=True)
            
        # return render_template("getSts.html")
    return render_template("datatools/getSts.html", siteTitle = siteTitle, len=len)
