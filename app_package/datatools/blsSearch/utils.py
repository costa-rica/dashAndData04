import os
import pandas as pd
from datetime import date
from datetime import timedelta
import datetime
import requests
# from requests.exceptions import MissingSchema
from flask import current_app
import numpy as np
from app_package import db
from app_package.modelsBls import Industrynames,Industryvalues, Commoditynames, Commodityvalues
from app_package.modelsCage import Cagecompanies
#added for BLS API call
from sqlalchemy import func
from dateutil.relativedelta import relativedelta
import json

periodsDict = {'M01': 1,'M02': 2,'M03': 3,'M04': 4,'M05': 5,'M06': 6,'M07': 7,
    'M08': 8,'M09': 9,'M10': 10,'M11': 11,'M12': 12,'M13': 13}
    
def checkStatusUtility(formDict):
    cs0=formDict.get('series_idCheckbox')
    cs1=formDict.get('industry_codeCheckbox')
    cs2=formDict.get('product_codeCheckbox')
    cs3=formDict.get('seasonalCheckbox')
    cs4=formDict.get('base_dateCheckbox')
    cs5=formDict.get('series_titleCheckbox')
    cs6=formDict.get('footnote_codesCheckbox')
    cs7=formDict.get('begin_yearCheckbox')
    cs8=formDict.get('begin_periodCheckbox')
    cs9=formDict.get('end_yearCheckbox')
    cs10=formDict.get('end_periodCheckbox')
    if formDict.get('periodicity')=="month":
        cs11='checked'
        cs12=None
        cs13=None
    elif formDict.get('periodicity')=="quarter":
        cs11=None
        cs12='checked'
        cs13=None
    else:
        cs11=None
        cs12=None
        cs13='checked'
    return (cs0,cs1,cs2,cs3,cs4,cs5,cs6,cs7,cs8,cs9,cs10,cs11,cs12,cs13)
    

def formatSeriesIdListUtil(seriesIdList):
    seriesIdList=seriesIdList.split(',')
    seriesIdList2=[]
    for i in seriesIdList:
        j=i.replace('\n','')
        seriesIdList2.append(j)
    return seriesIdList2


def priceIndicesToDf(seriesIdList,dfType):
    listDict={}
    
    for i in seriesIdList:
        if dfType=='Industry':
            series = Industrynames.query.filter_by(series_id=i).first()
        else:
            series = Commoditynames.query.filter_by(series_id=i).first()
        
        yearsList = [j.year for j in series.values]
        periodsList = [j.period for j in series.values]
        valuesList = [j.value for j in series.values]
        listDict[i] = [yearsList,periodsList, valuesList]
    dfDict={}
    for i in listDict:
        df=pd.DataFrame(list(zip(listDict[i][0],listDict[i][1],listDict[i][2])), columns=['years','periods','values'])
        df.replace({'periods':periodsDict}, inplace=True)
        df=df[df.periods!=13]
        df['date']=pd.to_datetime(dict(year=df.years,month=df.periods,day=1))
        
        df.drop(columns=['years','periods'], inplace=True)
        df.set_index(['date'], inplace=True)
        df.rename(columns={'values':i}, inplace=True)
        dfDict[i]=df
    
    dfExcel=list(dfDict.values())[0]
    if len(seriesIdList)>1:
        for i in dfDict:
            if i!=list(dfDict.keys())[0]:
                dfExcel=pd.merge(dfExcel,dfDict[i], how='outer',left_index=True, right_index=True)
    
    dfExcel.reset_index(inplace=True)
    dfExcel.sort_values(by=['date'],ascending = False, inplace = True)
    return dfExcel



def updateDbWithApi(seriesIdListClean, table_name):
    
    db_date_is_good_until, api_search_list = checkDbForExistingData(seriesIdListClean, table_name)
    print('successfully checked Db for Existing Data. The follwing indicies need updating: ',api_search_list)
    if len(api_search_list)>0:
        json_data = blsApiCall(db_date_is_good_until, api_search_list)
        df_dict = makeDfDictionary(api_search_list, json_data)
        print('succesfully created df_dict')
        deleteOldRows(table_name, df_dict)
        print('Succesfully update! Appeneded ', table_name,' for :',api_search_list)
    else:
        print('All requested series_ids already up to date. No BLS API call necessary.')
    



def annualizeDf(df):
    df['year']=pd.DatetimeIndex(df['date']).year
    df=df.groupby(['year']).mean()
    df.reset_index(inplace=True)
    df.sort_values(by=['year'],ascending = False, inplace = True)
    print('dtypes for annualizedDF:::', df.dtypes)
    return df


def quarterizeDf(df):#probabaly need to add a column that has dates, sort on date, then remove date before return
    quarterDict = {1:'Q1',2:'Q1', 3:'Q1',4:'Q2',5:'Q2',6:'Q2',7:'Q3',8:'Q3',9:'Q3',10:'Q4',11:'Q4',12:'Q4'}
    monthDict= {'Q1':1,'Q2':4,'Q3':7,'Q4':10}
    # monthDict= {1:'Q1',4:'Q2',7:'Q3',10:'Q4'}
    df['quarter'] = pd.DatetimeIndex(df['date']).month
    df['year'] = pd.DatetimeIndex(df['date']).year.astype(str)
    df.replace({'quarter':quarterDict}, inplace=True)
    df['quarter-year'] = df[['quarter','year']].agg('-'.join,axis=1)
    df=df.groupby(['quarter-year']).mean()
    df.reset_index(inplace=True)
    df['year']= df['quarter-year'].str[3:].astype('int32')
    df['month'] = df['quarter-year'].str[0:2].astype('str')
    df['month'].replace(monthDict, inplace = True)
    df['day'] = 1
    df['date'] = pd.to_datetime(df[['year','month','day']])
    df.sort_values(by=['date'],ascending = False, inplace = True)
    df.drop(columns=['year','month','day','date'], inplace = True)
    return df

 
def checkDbForExistingData(seriesIdListClean, table_name):
    for table in db.Model.__subclasses__():
        if table.__tablename__ == table_name:
            database_to_search = table
            print('database_to_search:::',type(database_to_search))
            print('table:::',type(table))

    api_search_list =[]
    for series in seriesIdListClean:
        max_year = db.session.query(func.max(database_to_search.year)).filter(
            database_to_search.series_id == seriesIdListClean[0]).first()[0]
        id_list = db.session.query(database_to_search.id, database_to_search.period).filter(
            database_to_search.series_id == seriesIdListClean[0],database_to_search.year == max_year).all()

        print('id_list::::', id_list)
        print('max_year::::', max_year)

        x=0
        for i in id_list:
            if int(i[1][1:3]) > x:
                x = int(i[1][1:3])
                id_of_max_period_from_series_id = i[0]#<----id_of_max_period_from_series_id is the
        #database_to_search.id for the most current entry of theseries_id in the database.
        
        month_value, year_value = db.session.query(database_to_search).filter(
            database_to_search.id == id_of_max_period_from_series_id).with_entities(
            database_to_search.period, database_to_search.year).first()
        month_value = int(month_value[1:])
        db_date = datetime.datetime.strptime(f'{year_value}-{month_value}-1','%Y-%m-%d').date()
        
        # BLS release dates vary between the 9th and 17th of the month. Here i'm assuming
        #all db is current up to 2 months and 13 days behind the current date. Or 
        #up to the 14th of the two months following the month in the db.
        #***idea: put release schedule in a dictionary and update db_date_is_good_until based on schedule.
        db_date_is_good_until = db_date +relativedelta(months=2)+relativedelta(days=13)
        
        current_date = datetime.datetime.now().date()
        if current_date >db_date_is_good_until:
            api_search_list.append(series)
    return (db_date_is_good_until, api_search_list)


def blsApiCall(db_date_is_good_until, api_search_list):
    headers = {'Content-type': 'application/json'}
    startYear=datetime.datetime.now().date() + relativedelta(years=-3)
    startYear=startYear.year
    endYear=db_date_is_good_until.year
    data = json.dumps({"seriesid": api_search_list,"startyear":startYear, 
                       "endyear":endYear,
                       'registrationkey':current_app.config['REGISTRATION_KEY']
                      })
    bls_pull = requests.post(current_app.config['BLS_API_URL'], data=data, headers=headers)
    print('API Status code:',bls_pull.status_code)
    if bls_pull.status_code != 200:
        return print('API call did not go through. Status is something other than 200.')
    json_data=json.loads(bls_pull.text)
    return json_data


def makeDfDictionary(api_search_list, json_data):
    df_dict={}
    for series in api_search_list:
        series_id_list = []
        year_list =[]
        period_list =[]
        value_list =[]
        footnote_codes_list = []
        series_count = api_search_list.index(series)
        print(series)
        print('makeDfDictionary -- json_data:::',json_data)
        try:
            for record in json_data['Results']['series'][series_count]['data']:
                series_id_list.append(json_data['Results']['series'][series_count]['seriesID'])
                year_list.append(record['year'])
                period_list.append(record['period'])
                value_list.append(record['value'])
                footnote_codes_list.append(record['footnotes'][0].get('code'))
            df_dict[series]=pd.DataFrame(list(zip(series_id_list,year_list,period_list,value_list,
                                                 footnote_codes_list)), columns=['series_id','year','period','value','footnote_codes'])
        except:
            print(series, 'has current data to update')
            
    for df in df_dict.values():
        df['id']=df.index
        df.set_index('id', inplace = True)
    
    return df_dict


def deleteOldRows(table_name, df_dict):
    import sqlalchemy as sa
    meta = sa.MetaData()
    # table_name = 'commodityvalues'
    for df in df_dict.values():
        sa_table = sa.Table(table_name, meta, autoload=True, autoload_with=db.engine)
        cond = df.apply(lambda row: sa.and_(sa_table.c['series_id'] == row['series_id'],
                                                sa_table.c['year'] == row['year'],
                                                sa_table.c['period'] == row['period']), axis=1)
        cond = sa.or_(*cond)

        # Define and execute the DELETE
        delete = sa_table.delete().where(cond)
        with db.engine.connect() as conn:
            conn.execute(delete)
        
        # Now you can insert the new data
        df.to_sql(table_name, db.engine, if_exists='append', index=False)


def seriesIdTitleListIndustry():
    listOfSeriesIds=db.session.query(Industryvalues.series_id).distinct().all()
    listOfSeriesIds=[i[0] for i in list(listOfSeriesIds)]
    indexNameTableObj = Industrynames.query.filter(Industrynames.series_id.in_(listOfSeriesIds)).all()
    
    indexSeriesIdTitleList=[]
    for i in indexNameTableObj:
        indexIdTitleList=[i.series_id,i.series_title]
        indexSeriesIdTitleList.append(indexIdTitleList)
    return indexSeriesIdTitleList


def seriesIdTitleListCommodity():
    listOfSeriesIds=db.session.query(Commodityvalues.series_id).distinct().all()
    listOfSeriesIds=[i[0] for i in list(listOfSeriesIds)]
    indexNameTableObj = Commoditynames.query.filter(Commoditynames.series_id.in_(listOfSeriesIds)).all()
    
    indexSeriesIdTitleList=[]
    for i in indexNameTableObj:
        indexIdTitleList=[i.series_id,i.series_title]
        indexSeriesIdTitleList.append(indexIdTitleList)
    return indexSeriesIdTitleList




def buildMetaDfUtil(seriesIdListClean,metaDataItemsList,dfType):
    metaDict={}
    for j in seriesIdListClean:
        if dfType == 'Industry':
            subList= [Industrynames.query.with_entities(getattr(Industrynames, i)).filter_by(
                series_id=j).first()[0] for i in metaDataItemsList]
        else:
            subList= [Commoditynames.query.with_entities(getattr(Commoditynames, i)).filter_by(
                series_id=j).first()[0] for i in metaDataItemsList]
        metaDict[j] = subList
        
    metaDict['Meta Data Row Headings']=metaDataItemsList
    metaDf=pd.DataFrame.from_dict(metaDict)

    cols = list(metaDf.columns)
    cols = [cols[-1]] + cols[:-1]
    metaDf = metaDf[cols]

    return metaDf



def makeExcelObj_priceindices(filePathAndName,metaDf,indexValuesDf,seriesIdList,metaDataItemsList,sheetName,
        periodicity):
    excelObj=pd.ExcelWriter(filePathAndName,datetime_format='yyyy-mm-dd')
    metaDf.to_excel(excelObj, sheet_name=sheetName, header=False,index=False)
    # print('metaDataItemsList:::',metaDataItemsList)
    #column count and row number for wrapping text and widening
    # rowWrap=metaDataItemsList.index('series_title')
    columnCount=len(seriesIdList)+1
    print('periodicity:::', periodicity)
    #adjust column width and make certain cells wrap
    worksheet=excelObj.sheets[sheetName]
    workbook=excelObj.book
    if periodicity == 'annual':
        print('are we getting the right format?')
        indexValuesDf=annualizeDf(indexValuesDf)
        izquerda_date_format_wb = workbook.add_format({'align': 'left'})
        worksheet.set_column(0,0,15,izquerda_date_format_wb)
    elif periodicity == 'quarter':
        indexValuesDf=quarterizeDf(indexValuesDf)
        izquerda_date_format_wb = workbook.add_format({'align': 'left'})
        worksheet.set_column(0,0,15,izquerda_date_format_wb)
    else:
        izquerda_date_format_wb = workbook.add_format({'align': 'left', 'num_format' : 'mm/dd/yyyy'})
        worksheet.set_column(0,0,15,izquerda_date_format_wb)
    
    indexValuesDf.to_excel(
        excelObj, sheet_name=sheetName,startrow=len(metaDf), header=False, index=False)

    cell_format_wrap_values=workbook.add_format({'align':'center','text_wrap':True, 'num_format':'00.0'})
    cell_format_wrap_meta=workbook.add_format({'align':'center','text_wrap':True})
    wrapRows=[]
    
    for row in metaDataItemsList:
        if row == 'series_title' or row == 'series_id':
            wrapRows.append(metaDataItemsList.index(row))
    
    #format date column:
    for row in range(len(metaDf),len(indexValuesDf)+len(metaDf)):
        worksheet.write(row,0,indexValuesDf.iloc[row-len(metaDf),0], izquerda_date_format_wb)
        # worksheet.write(row,0,'year should go here', izquerda_date_format_wb)
    
    for col in range(1,columnCount):
        # for row in range(len(metaDf),len(indexValuesDf)+len(metaDf)):
        for row in range(len(metaDf),len(indexValuesDf)+len(metaDf)):
            try:
                worksheet.write(row,col,indexValuesDf.iloc[row-len(metaDf),col], cell_format_wrap_values)
            except TypeError:
                #TypeError is the error for trying to format na cells
                # worksheet.write(row,col,'Empty Cell', cell_format_center)
                pass
                
    # set wrap and width of column if length of cell is beyond an amount
    for row in wrapRows:
        for i in range(1,columnCount):
            if len(str(metaDf.iloc[row,i])) >10:
                worksheet.set_column(i,i,11, cell_format_wrap_meta)
            if len(str(metaDf.iloc[row,i])) >20:
                worksheet.set_column(i,i,15, cell_format_wrap_meta)
            if len(str(metaDf.iloc[row,i])) >83:
                worksheet.set_column(i,i,20, cell_format_wrap_meta)
            if len(str(metaDf.iloc[row,i])) >183:
                worksheet.set_column(i,i,30, cell_format_wrap_meta)

    worksheet.freeze_panes(len(metaDf),1)
    return excelObj

    
def makeSearchExactDict(formDict):
    searchStringDict={}
    exactDict={}
    for i,j in formDict.items():
        if i != 'searchCage' and i[-5:] != 'Exact':
            searchStringDict[i]=j
        elif i[-5:] == 'Exact':
            exactDict[i[:-5]]=j
    return (searchStringDict,exactDict)
    
    
