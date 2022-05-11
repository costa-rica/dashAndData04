from flask import Blueprint

from flask import render_template, url_for, redirect, flash, request, abort, session,\
    Response, current_app, send_from_directory
import os
from app_package.datatools.cage_search.utils import makeSearchExactDict, \
    searchQueryCageToDf, cageExcelObjUtil
# from app_package.datatools.cage_search.forms import CageForm
import logging
from app_package.utils import logs_dir


#Setting up Logger
formatter = logging.Formatter('%(asctime)s:%(name)s:%(message)s')
formatter_terminal = logging.Formatter('%(asctime)s:%(filename)s:%(name)s:%(message)s')

logger_cage = logging.getLogger(__name__)
logger_cage.setLevel(logging.DEBUG)
logger_terminal = logging.getLogger('terminal logger')
logger_terminal.setLevel(logging.DEBUG)

file_handler = logging.FileHandler(os.path.join(logs_dir,'cage.log'))
file_handler.setFormatter(formatter)

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter_terminal)

logger_cage.addHandler(file_handler)
logger_terminal.addHandler(stream_handler)

#End set up logger

datatools_cage = Blueprint('datatools_cage', __name__)

    
@datatools_cage.route('/cageCodeSearch',methods=['POST','GET'])
def cageCodeSearch():

    siteTitle='CAGE Code Lookup'
    searchDictClean={'companyName':'Company Name', 'companyNameSub':'Company Name (Subsidiary)','cageCode': 'CAGE Code',
        'address': 'Address', 'city': 'City', 'state': 'State'}
    if request.method=="POST":
        logger_cage.info(f'CAGE POST request made')
        formDict = request.form.to_dict()

        logger_terminal.debug(f'formDIct:::{formDict}')
        if formDict.get('clearButton'):
            return redirect(url_for('datatools_cage.cageCodeSearch'))

        searchStringDict,exactDict = makeSearchExactDict(formDict)
        #re-Key searchStringDict for webpage
        searchDictClean={'companyName':'Company Name', 'companyNameSub':'Company Name (Subsidiary)','cageCode': 'CAGE Code',
            'address': 'Address', 'city': 'City', 'state': 'State'}
        searchStringDict={searchDictClean[i]:j for i,j in searchStringDict.items()}
        exactDict={searchDictClean[i]:j for i,j in exactDict.items()}
        

        logger_terminal.debug(f'searchStringDict:::{searchStringDict}')
        logger_terminal.debug(f'exactDict:::{exactDict}')

        count=0
        for i in searchStringDict.values():
            count=count + len(i)
        if count<2:
            flash(f'Query too broad. Must enter at least two search characters to narrow search.', 'warning')
            return redirect(url_for('datatools_cage.cageCodeSearch'))

        df=searchQueryCageToDf(formDict)

        print('df:::')
        print(df)
        print('formDict::::', formDict)
        resultsCount = len(df)
        if resultsCount>10000:
            flash(f'Query beyond 10,000 row limit. Must enter more search criteria to narrow search.', 'warning')
            return redirect(url_for('datatools_cage.cageCodeSearch'))
        if formDict.get('searchCage')=='search':
            columnNames = df.columns
            dfResults = df.to_dict('records')
            print('searchStringDict:::',searchStringDict)
            
            return render_template('datatools/cageCodeSearch.html', siteTitle=siteTitle, columnNames=columnNames, dfResults=dfResults,
                len=len, searchStringDict=searchStringDict, exactDict=exactDict, searchDictClean=searchDictClean,
                resultsCount='{:,}'.format(resultsCount))
        if formDict.get('searchCage')=='download':
            filePathAndName=os.path.join(current_app.static_folder, 'cageSearch','CAGE_SearchResults.xlsx')
            excelObj=cageExcelObjUtil(filePathAndName,df)
            excelObj.close()
            return send_from_directory(os.path.join(current_app.static_folder, 'cageSearch'),'CAGE_SearchResults.xlsx', as_attachment=True)
    return render_template('datatools/cageCodeSearch.html', siteTitle=siteTitle, searchDictClean=searchDictClean, len=len)
