from docx2python import docx2python
import os
import json
from flask import current_app


def blogs_dict_dict_util(blogs_file_name_list, blog_json_files_folder):
    blogs_dict_dict_result={}
    for i in blogs_file_name_list:
        blog_dict_file = os.path.join(blog_json_files_folder,i)
        with open(blog_dict_file,'r') as f:
            blogs_dict_dict_result[i[:-5]] = json.load(f)
            f.close
    return blogs_dict_dict_result

#ordered_blog_dict_dict is dict where each key/value is entered in by most recent date_published
def ordered_blog_dict_dict_util(date_pub_list, blogs_dict_dict):
    ordered_blog_dict_dict={}
    for date in date_pub_list:
        for temp_dict in list(blogs_dict_dict.values()):
            temp_blog_name=temp_dict['blog_name']
            temp_blog_date=temp_dict['date_published'][1]
            if date == temp_blog_date:
                ordered_blog_dict_dict[temp_blog_name] = temp_dict
                del blogs_dict_dict[temp_blog_name]
    return ordered_blog_dict_dict

# blog_dicts_for_index is a abbrev dictionary of blog_name:items needed for blog_index.html
def blog_dicts_for_index_util(ordered_blog_dict_dict):
    blog_dicts_for_index = {}
    for blog_name,blog_dict_from_json in ordered_blog_dict_dict.items():
        temp_blog_dict={}

        temp_blog_dict['blog_name']=blog_name
        #Get title 
        temp_blog_dict['title']=[blog_dict_from_json["1"][1]]
        #Get first paragraph
        if blog_dict_from_json.get('index_description'):
            temp_blog_dict['index_description']=blog_dict_from_json["index_description"]
        else:
            if blog_dict_from_json.get("3")[1] !='':
                temp_blog_dict['index_description']=blog_dict_from_json["3"][1]
            else:
                temp_blog_dict['index_description']=blog_dict_from_json["4"][1]

        #Get location
        if blog_dict_from_json.get('app_location'):
            temp_blog_dict['app_location']=blog_dict_from_json["app_location"][1]
        
        if blog_dict_from_json.get('date_published'):

            temp_blog_dict['date_published']=blog_dict_from_json['date_published'][1]
        
        # add blog_dict to blog_dicts
        blog_dicts_for_index[blog_name]=temp_blog_dict
    return blog_dicts_for_index

def wordToJson(word_doc_file_name, word_doc_path, blog_name, date_published, description='',link=''):
    
    print('word_doc_path:::', word_doc_path)
    print('word_doc_file_name:::', word_doc_file_name)

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

    print('***doc_result_html.document[0] (in wordToJson)*** ')
    print(doc_result_html.document[0])

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
        #codeblock_type1
        elif i.find(r'<span style="color:FFFFFF">')>-1:
            adj=i.find(r'<span style="color:FFFFFF">')
            blog_dict[count]=['codeblock_type1',i[27+adj:-len('</span>')]]
        else:
            blog_dict[count]=['',i]
        count+=1

    # json_file_name = blog_name+'.json'

    return blog_dict


def consecutive_row_util(blog_dict):
    blog_dict_reverse = {i:blog_dict[i] for i in reversed(blog_dict.keys())}
    new_dict={}; count=1
    for i,j in blog_dict_reverse.items():
        if count==1:
            new_dict[i]=j
            im2='';jm2=['',''];im1=i;jm1=j
        elif j[0]==jm1[0]=='codeblock_type1':
            new_dict[i]=[j[0],j[1]+'<br>'+jm1[1]]
            del new_dict[im1]
            i_m2='';jm2=['',''];im1=i;jm1=[j[0],j[1]+'<br>'+jm1[1]]
        elif j[0]==jm2[0]=='codeblock_type1' and jm1[0]=='new lines':
            new_dict[i]=[j[0],j[1]+'<br>'+jm1[1]+'<br>'+jm2[1]]
            del new_dict[im1];del new_dict[im2]
            im1=i;jm1=[j[0],j[1]+'<br>'+jm1[1]+'<br>'+jm2[1]];im2='';jm2=['','']
        elif j[0]!=jm1[0]:
            new_dict[i]=j
            im2=im1;jm2=jm1;im1=i;jm1=j
        else:
            new_dict[i]=j
            im2=im1;jm2=jm1;im1=i;jm1=j
        count+=1
    
    new_dict_reverse = {i:new_dict[i] for i in reversed(new_dict.keys())}
    new_dict_reverse_formatted =json.dumps(new_dict_reverse, ensure_ascii=False).encode('utf8')

    #convert to a dictionary
    dictWithEscaping=json.loads(new_dict_reverse_formatted.decode())

    #Script to remove double quoutes from links, but any double qoutes in j[1]
    dictNoEscaping={i:([j[0],j[1].replace('"','')] if type(j)==list else j )for i,j in dictWithEscaping.items() }
    # dictNoEscaping
    #unfortunately, this dict uses single qoutes. in order to convert it to double qoutes for json, we need json.dumps

    #convert dictNoEscaping into a string with double qoutes (i.e "keys":"values")
    stringNoEscaping=json.dumps(dictNoEscaping, ensure_ascii=False).encode('utf8')


    return stringNoEscaping

