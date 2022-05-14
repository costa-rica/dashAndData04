# from time import strftime
from flask import Blueprint
from flask import render_template, url_for, redirect, flash, request,current_app
import os
from datetime import datetime
import time
from sqlalchemy import func
import json
from flask_login import login_user, current_user, logout_user, login_required
from app_package.blog.forms import BlogPostForm
from app_package.blog.utils import wordToJson, blogs_dict_dict_util, \
    ordered_blog_dict_dict_util, blog_dicts_for_index_util, consecutive_row_util
from app_package.models import Users, Posts, PostsToHtml, PostsToHtmlTagChars
from app_package import db
from sqlalchemy import func 
import logging
from app_package.utils import logs_dir


#Setting up Logger
formatter = logging.Formatter('%(asctime)s:%(name)s:%(message)s')
formatter_terminal = logging.Formatter('%(asctime)s:%(filename)s:%(name)s:%(message)s')

logger_blog = logging.getLogger(__name__)
logger_blog.setLevel(logging.DEBUG)
logger_terminal = logging.getLogger('terminal logger')
logger_terminal.setLevel(logging.DEBUG)

file_handler = logging.FileHandler(os.path.join(logs_dir,'blog.log'))
file_handler.setFormatter(formatter)

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter_terminal)

logger_blog.addHandler(file_handler)
logger_terminal.addHandler(stream_handler)

#End set up logger


blog = Blueprint('blog', __name__, __name__,url_prefix='/blog')

    
@blog.route("/", methods=["GET"])
def blog_index():
    logger_terminal.info(f'****Blog Index Accessed*****')

    #Get blog json file path:
    # blog_json_files_folder=os.path.join(current_app.config['STATIC_PATH'], 'blogs')

    # # Get list of json blog file names
    # blogs_file_name_list = os.listdir(blog_json_files_folder)
    # blogs_file_name_list.remove('uploaded_word')
    
    # #get all blog jsons into blogs_dict, key names 'blog01', values corresponding json file dicts
    # blogs_dict_dict=blogs_dict_dict_util(blogs_file_name_list, blog_json_files_folder)

    # blogs_file_name_list=[i[:-5] for i in blogs_file_name_list]

    # date_pub_list =[j['date_published'][1] for i,j in blogs_dict_dict.items()]

    # date_pub_list.sort(reverse=True)

    # #ordered_blog_dict_dict is like blogs_dict_dict, each key/value is entered in by most recent date_published
    # ordered_blog_dict_dict=ordered_blog_dict_dict_util(date_pub_list, blogs_dict_dict)

    # # blog_dicts_for_index is a abbrev dictionary of blog_name:items needed for blog_index.html
    # # blog_dicts_for_index is sorted by the previous lines
    # blog_dicts_for_index = blog_dicts_for_index_util(ordered_blog_dict_dict)

    #sorted list of published dates
    date_pub_list=[i.date_published for i in Posts.query.all()]
    # create new list of sorted datetimes into increasing order
    sorted_date_pub_list = sorted(date_pub_list)
    #reverse new list
    sorted_date_pub_list.sort(reverse=True)

    #make dict of title, date_published, description
    items=['blog_title', 'blog_description','date_published']
    posts_list = Posts.query.all()
    blog_dict_for_index_sorted={}
    for i in sorted_date_pub_list:
        for post in posts_list:
            if post.date_published == i:
                temp_dict={key: (getattr(post,key) if key!='date_published' else getattr(post,key).strftime("%m/%d/%Y") ) for key in items}
                temp_dict['blog_name']='blog'+str(post.id).zfill(4)
                # temp_dict={key: (getattr(post,key) if key=='date_published' else getattr(post,key)[:9] ) for key in items}
                blog_dict_for_index_sorted[post.id]=temp_dict
                posts_list.remove(post)



    return render_template('blog/index.html', blog_dicts_for_index=blog_dict_for_index_sorted)
    
@blog.route("/<blog_name>", methods=["GET"])
def blog_template(blog_name):
    logger_blog.info(f'**Accessed:: {blog_name}')
    print('blog_name[-4:]::', blog_name[-4:])
    post_id=int(blog_name[-4:])
    post=PostsToHtml.query.filter(post_id==post_id).all()
    blog_dict={i.word_row_id: [i.row_tag,i.row_going_into_html] for i in post}


    # # Old ##
    # blog_json_files_folder=os.path.join(current_app.config['STATIC_PATH'], 'blogs')
    # blog_dict_file = os.path.join(blog_json_files_folder,blog_name+'.json')
    
    # # Problem loading values with double qoutes
    # with open(blog_dict_file) as blog_dict_file:
    #     blog_dict = json.load(blog_dict_file)
    
    # if blog_dict.get('0'):
    #     del blog_dict['0']
    # if blog_dict.get('blog_name'):
    #     del blog_dict['blog_name']
    # if blog_dict.get('index_description'):
    #     del blog_dict['index_description']
    # if blog_dict.get('app_location'):
    #     del blog_dict['app_location']

    # # print('blog_dict::::', blog_dict)

    return render_template('blog/template.html', blog_dict=blog_dict)

@blog.route("/post", methods=["GET","POST"])
@login_required
def blog_post():
    blog_word_docs_folder=os.path.join(current_app.config['STATIC_PATH'], 'blog_word_docs')
    form = BlogPostForm()

    if request.method == 'POST' and 'word_doc_name' in request.files:
        formDict = request.form.to_dict()
        filesDict = request.files.to_dict()


        uploaded_file = request.files['word_doc_name']
        word_doc_file_name = uploaded_file.filename

        # word_doc_path=os.path.join(os.path.join(blog_json_files_folder,'uploaded_word'))
        
        # if /static/blogs and /static/blogs/uploaded_word don't exist      
        try:
            os.makedirs(blog_word_docs_folder)
        except:
            logger_terminal.info(f'folder exists')
            
        uploaded_file.save(os.path.join(blog_word_docs_folder,word_doc_file_name))

        #get blog_id
        # blogs_file_name_list = os.listdir(blog_json_files_folder)
        # blogs_file_name_list.remove('uploaded_word')
        # print('blogs_file_name_list::::', blogs_file_name_list)
        # blog_int_value_list = [int(i[4:8]) for i in blogs_file_name_list]
        # if len(blog_int_value_list)>0:
        #     # print('***This is where the ')
        #     #this db.func..Posts.id get's the max id from the Posts table
        #     blog_name = 'blog'+str(db.session.query(func.max(Posts.id)).first()[0]+1).zfill(4)
        # else:
        #     blog_name = 'blog0001'
        #     print('***this shouldnot show up*****')

        if len(Posts.query.all())>0:
            blog_name = 'blog'+str(db.session.query(func.max(Posts.id)).first()[0]+1).zfill(4)
        else:
            blog_name = 'blog0001'

        # print('blog_name:::', blog_name)
        #get word_doc_file_name
        

        #get date_published
        # date_published = formDict.get('date_published')

### TODO: create Posts row for new posts - doens't have to be fully filled out.


        post_id = wordToJson(word_doc_file_name, blog_word_docs_folder, blog_name,
            formDict.get('date_published'), description=formDict.get('blog_description'),
            link=formDict.get('link_to_app'))
        
        # print('***blog_dict (after wordToJson)*** ')
        # print(blog_dict)

        #consecutive row similar tag script. Returns string in dict form.
        # new_dict_reverse_formatted= json.loads(consecutive_row_util(post_id))
        new_post_rows= consecutive_row_util(post_id)
        print('****new_post_rows****')
        print(new_post_rows)
        # # print('new_dict_reverse_formatted**')
        # # print(type(new_dict_reverse_formatted))
        # # print(new_dict_reverse_formatted)
        # with open(os.path.join(current_app.config['STATIC_PATH'], 'blogs',blog_name+'.json'),
        #     'w') as output:
        #     json.dump(new_dict_reverse_formatted,output)

        # #open json file with new blog post
        # with open(os.path.join(current_app.config['STATIC_PATH'], 'blogs',blog_name+'.json'),'r') as f:
        #     blog_dict = json.load(f)
        #     f.close
        # #get description
        # if formDict.get('blog_description')!='':
        #     description=formDict.get('blog_description')
        # else:
        #     if blog_dict["3"][1] !='':
        #         description=blog_dict["3"][1]
        #     else:
        #         description=blog_dict["4"][1]

# ####TODO: this becomes and update query to exisiting Posts entry
# # Make post object
#         new_post = Posts(
#             blog_title=blog_dict['1'][1],
#             blog_description = description,
#             timestamp = datetime.now(),
#             date_published = datetime.strptime(formDict.get('date_published'), "%Y-%m-%d"),
#             link_to_app = formDict.get('link_to_app'),
#             word_doc = word_doc_file_name,
#             json_file = blog_name +'.json',
#             user_id = current_user.id
#             )
# #add post object to 
#         db.session.add(new_post)
#         db.session.commit()



        flash(f'Post added successfully!', 'success')
        return redirect(url_for('blog.blog_post'))
    return render_template('blog/post.html', form=form)

@blog.route("/blog_user_home", methods=["GET","POST"])
@login_required
def blog_user_home():
    all_posts=Posts.query.all()
    posts_details_list=[]
    for i in all_posts:
        posts_details_list.append([i.id, i.blog_title, i.date_published.strftime("%m/%d/%Y"),
            i.blog_description, i.word_doc])




    column_names=['id', 'blog_title','date_published',
         'blog_description','json_file', 'word_doc']

    if request.method == 'POST':
        formDict=request.form.to_dict()
        print('formDict::', formDict)
        blog_id=formDict.get('delete_record_id')
        return redirect(url_for('blog.blog_delete', blog_id=blog_id))

    return render_template('blog/user_home.html', posts_details_list=posts_details_list, len=len,
        column_names=column_names)

@blog.route("/delete/<blog_id>", methods=['GET','POST'])
@login_required
def blog_delete(blog_id):
    print('****In delete route****')
    print('blog_id:::::', blog_id)

    post_to_delete = Posts.query.get(int(blog_id))
    blog_name = 'blog'+blog_id.zfill(4)
    print(post_to_delete)


    # #delete json file
    # blog_json_path = os.path.join(current_app.config['STATIC_PATH'], 'blogs')
    # try:
    #     os.remove(os.path.join(blog_json_path, post_to_delete.json_file))
    # except:
    #     print('no blog json file')
    
    #delete word document
    word_doc_path = os.path.join(current_app.config['STATIC_PATH'],'blog_word_docs')
    try:
        os.remove(os.path.join(word_doc_path, post_to_delete.word_doc))
    except:
        print('no word document file exists')
    
    #delete images folder
    images_folder = os.path.join(current_app.config['STATIC_PATH'], 'images')
    print('images path: ', os.path.join(images_folder, blog_name))
    try:
        os.rmdir(os.path.join(images_folder, blog_name)) 
    except:
        print('no images folder for this blog exists')

    #delete db row

    # Posts.query.filter_by(id=int(blog_id)).delete()
    db.session.query(Posts).filter(Posts.id==blog_id).delete()
    db.session.query(PostsToHtml).filter(PostsToHtml.post_id==blog_id).delete()
    db.session.query(PostsToHtmlTagChars).filter(PostsToHtmlTagChars.post_id==blog_id).delete()
    db.session.commit()

    print('blog post deleted for ::: ', blog_id)

    return redirect(url_for('blog.blog_user_home'))