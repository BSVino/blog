import os
import shutil
import time
import sys
import argparse
import re
import datetime
import markdown
import cgi
from email import utils

import subprocess
import platform

########################## Command Line Arguments ##########################

parser = argparse.ArgumentParser(description="Compile OpenGL documentation, generate a static webpage.")

parser.add_argument('--full', dest='buildmode', action='store_const', const='full', default='fast', help='Full build (Default: fast build)')

########################## Print  ##########################

args = parser.parse_args()

if args.buildmode == 'full':
  print "FULL BUILD"
  sys.path.append("htmlmin")
  import htmlmin
else:
  print "FAST BUILD"

def create_directory(dir):
  if not os.path.exists(dir):
      os.makedirs(dir)  

########################## Output Directory Selection ########################## 
 
output_dir = "htdocs/"

print "Resetting output dir..."
while os.path.exists(output_dir):
  try:
    shutil.rmtree(output_dir);
  except:
    pass # It gives an error sometimes. If it didn't work try again.

while not os.path.exists(output_dir):    
  try:
    create_directory(output_dir)
  except:
    pass # It gives an error sometimes. If it didn't work try again.
    
#################### Copy "html/copy" Files To Output Directory ####################

f = []
d = []
for (dirpath, dirnames, filenames) in os.walk("html/copy"):
  dirpath = dirpath[10:]

  if "test" in dirpath:
    continue
    
  d.append(dirpath)
  for file in filenames:
    if file[-3:] != '.js' and file[-4:] != '.css' and file[-4:] != '.png' and file[-5:] != '.htm':
      continue
    f.append(dirpath + "/" + file)

for directory in d:
  create_directory(output_dir + directory)
  
for file in f:
  shutil.copy("html/copy/" + file, output_dir + file)

post_files = []
for (dirpath, dirnames, filenames) in os.walk("html/posts"):
  dirpath = dirpath[11:]

  for file in filenames:
    post_files.append(dirpath + "/" + file)
  
print "Copied " + str(len(f)) + " files"
print "Reading templates..."

header_fp = open("html/header.htm")
header = header_fp.read()
header_fp.close()

footer_fp = open("html/footer.htm")
footer = footer_fp.read()
footer_fp.close()

index_fp = open("html/index.htm")
index_text = index_fp.read()
index_fp.close()

rss_fp = open("html/rss.xml")
rss = rss_fp.read()
rss_fp.close()

print "Done."

common_words = open("commonwords.txt").read().splitlines()

footer = footer.replace("{$gentime}", time.strftime("%d %B %Y at %H:%M:%S GMT", time.gmtime()));
index_text = index_text.replace("{$gentime}", time.strftime("%d %B %Y at %H:%M:%S GMT", time.gmtime()));

posts = {}
common_post_words = {}
post_times = {}

for post in post_files:
  if "drafts" in post:
    continue
 
  post_fp = open("html/posts" + post)

  post_text = post_fp.read()

  post_fp.close()

  post_time = 0
  post_title = ""

  for line in open("html/posts" + post):
    if line[0:5] == "Time:":
      post_time = int(line[6:])
    elif line[0:6] == "Title:":
      post_title = line[6:].strip()

    if line.strip() == "":
      break

  if post_time == 0 or len(post_title) == 0:
    print "Post " + post + " in invalid."
    die

  index = post_text.find('\n')
  while index > 0:
    post_text = post_text[index+1:]
    index = post_text.find('\n')

  splits = re.findall(r"[\w']+", post_text)
  common_words_dict = {}
  for word in splits:
    word = word.lower()

    if len(word) <= 1:
      continue

    if word.isdigit():
      continue;

    if word in common_words_dict:
      common_words_dict[word] += 1
    else:
      common_words_dict[word] = 1

  common_post_words_unabridged = [[k, common_words_dict[k], 0.0] for k in sorted(common_words_dict, key=common_words_dict.get, reverse=True)]
  common_post_words[post] = {}
  k = 0
  total_word_count = 0
  for word in common_post_words_unabridged:
    if word[0] in common_words:
      continue
    common_post_words[post][k] = word
    total_word_count += word[1]

    k += 1
    if k > 50:
      break

  for k in common_post_words[post]:
    common_post_words[post][k][2] = float(common_post_words[post][k][1])/total_word_count

  posts[post] = {
    'filename': post,
    'time': post_time,
    'title': post_title,
    'text': markdown.markdown(post_text.strip())
  }

  post_times[int(post_time)] = post

post_similarities = {}
for post in common_post_words:
  for other_post in common_post_words:
    if post == other_post:
      continue;

    for word_id in common_post_words[post]:
      word = common_post_words[post][word_id][0]
      for other_word_id in common_post_words[other_post]:
        other_word = common_post_words[other_post][other_word_id][0]
        if word == other_word:
          if post not in post_similarities:
            post_similarities[post] = {}
          if other_post not in post_similarities[post]:
            post_similarities[post][other_post] = 0
          post_similarities[post][other_post] += common_post_words[post][word_id][2] * common_post_words[other_post][other_word_id][2]

  sorted_similarity_list = sorted(post_similarities[post].items(), key=lambda x: x[1], reverse=True)
  post_similarities[post]['similar_list'] = sorted_similarity_list

for post in posts:
  posts[post]['similar'] = []

for post in post_similarities:
  similar_posts = post_similarities[post]['similar_list']

  num_added = 0
  similar_length = len(similar_posts)
  k = -1
  while num_added < 3:
    k += 1
    if k >= similar_length:
      break;

    other_post = similar_posts[k][0]
    if post in posts[other_post]['similar']:
      continue

    if post_similarities[other_post][post] > post_similarities[post][other_post]:
      continue

    posts[post]['similar'].append(other_post)
    num_added += 1

post_index = 1
posts_ordered = []
posts_order = {}
for key in sorted(post_times):
  post_time = post_times[int(key)]
  post = posts[post_time]

  posts_ordered.append(post['filename'])
  posts_order[post['filename']] = post_index

  post_index += 1


post_index = 1

for post_filename in posts_ordered:
  post = posts[post_filename]

  date_from_timestamp = datetime.datetime.fromtimestamp(post['time'])
  text_timestamp = date_from_timestamp.strftime('%B ' + str(date_from_timestamp.day) + ', %Y')
  signature = '<a href="/">Jorge Rodriguez</a>, <a href="' + str(post_index) + '.htm">' + text_timestamp + '</a>'

  post_header = header.replace("{$post}", post['title'])
  post_footer = footer.replace("{$date}", signature)

  similar_posts = "<h2>Similar:</h2><ul>"
  for similar_post in post['similar']:
    similar_posts += "<li><a href='" + str(posts_order[similar_post]) + ".htm'>" + posts[similar_post]['title'] + "</a></li>"
  similar_posts += "</ul>"

  post_footer = post_footer.replace("{$similar}", similar_posts)

  post_html = post_header
  post_html += post['text']
  post_html += post_footer

  post_filename = "htdocs/" + str(post_index) + ".htm"
  post_fp = open(post_filename, "w")
  post_fp.write(post_html)
  post_fp.close()

  post_index += 1


post_index -= 1
index_post_list = "<ul>"

year = datetime.datetime.fromtimestamp(posts[posts_ordered[len(posts_ordered)-1]]['time']).strftime('%Y')
index_post_list += "<h2>" + year + "</h2>"

rss_entries = ""

for post_filename in reversed(posts_ordered):
  post = posts[post_filename]

  date_from_timestamp = datetime.datetime.fromtimestamp(post['time'])
  post_year = date_from_timestamp.strftime('%Y')
  if not post_year == year:
    year = post_year
    index_post_list += "<h2>" + year + "</h2>"

  text_timestamp = date_from_timestamp.strftime('%B ' + str(date_from_timestamp.day))

  index_post_list += '<li><a href="' + str(post_index) + '.htm">' + post['title'] + "</a> - <em>" + text_timestamp + "</em></li>"

  rss_entries += "<item>"
  rss_entries += "<title>" + cgi.escape(post['title']) + "</title>"
  rss_entries += "<description>" + cgi.escape(post['text']) + "</description>"
  rss_entries += "<link>http://www.vinoisnotouzo.com/blog/" + str(post_index) + ".htm</link>"
  rss_entries += "<guid>http://www.vinoisnotouzo.com/blog/" + str(post_index) + ".htm</guid>"
  rss_entries += "<pubDate>" + utils.formatdate(time.mktime(date_from_timestamp.timetuple())) + "</pubDate>"
  rss_entries += "</item>"

  post_index -= 1

index_post_list += "</ul>"
index_fp = open("htdocs/index.htm", "w")
index_fp.write(index_text.replace("{$postlist}", index_post_list))
index_fp.close()

rss_fp = open("htdocs/rss.xml", "w")
rss_fp.write(rss.replace("{$entries}", rss_entries))
rss_fp.close()

