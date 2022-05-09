from docx2python import docx2python
import os
import json
from flask import current_app
import time
from datetime import datetime
import pathlib

def wordToJson(word_doc_file_name, word_doc_path, blog_name, date_published, description='',link=''):
    
    doc_result_html = docx2python(os.path.join(word_doc_path,word_doc_file_name),html=True)
    
    #all images saved
    images_folder = os.path.join(current_app.config['STATIC_PATH'], 'images')
    #Save pictures to 
    docx2python(os.path.join(word_doc_path,word_doc_file_name), os.path.join(images_folder,blog_name))

    blog_dict={}
    # blog_dict[0] = blog_id
    blog_dict["blog_name"]=blog_name

    blog_dict['date_published'] = ['date_published',date_published]
    if description != '':
        blog_dict['index_description']=description
    if link!='':
        blog_dict["app_location"] = ['href',link]

    count=1

    for i in doc_result_html.document[0][0][0]:

        if count ==1:
            blog_dict[count]=['h1',i]
        elif i=='':
            blog_dict[count]=['new lines',i]
        elif i[:3]=='--\t':
            if i.find('font-size:20pt')!=-1:
                #this means font is 10 point in word, and indent
                line=i[len('--\t<span style="font-size:20pt">'):-len('</span>')]
                blog_dict[count]=['ul and indent',line]
            else:
                #no indent
                blog_dict[count]=['ul',i[2:]]
        elif i[:4]=='Gif ' or i[:4]=='Figu' or i[:4]=='Code':
            blog_dict[count]=['image_title',i]
        elif i[:10]=='----media/':
            image_name= i[10:-4]
            html_image_path=f"../static/images/{blog_name}/{image_name}"
            blog_dict[count]=['image',html_image_path]
        elif i[:3]=='<u>' or i[:3]=='<a ':
            blog_dict[count]=['html',i]
        elif i[:3]=='<h1':
            blog_dict[count]=['h2',i[4:-5]]
        elif i[:29]=='<span style="font-size:20pt">':
            blog_dict[count]=['indent',i[29:-len('</span>')]]
    #code snippet
        elif i[:41]=='<span style="background-color:lightGray">':
            blog_dict[count]=['codeblock',i[41:-len('</span>')]]
        else:
            blog_dict[count]=['',i]
        count+=1
    
    json_file_name = blog_name+'.json'

    with open(os.path.join(current_app.config['STATIC_PATH'], 'blogs',json_file_name),'w') as output:
        json.dump(blog_dict,output)

