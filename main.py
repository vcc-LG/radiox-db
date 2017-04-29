from bs4 import BeautifulSoup
import urllib.request
import urllib.error
import os, sys
import datetime
from dateutil.relativedelta import relativedelta
import discogs_client
from pymongo import MongoClient
import wikipedia
import re

d  = discogs_client.Client('radioXapp/0.1', user_token="aSrxNAkKdICMKfPGnIGJbqJwSdCPZdhflOjtuOLn")

client = MongoClient()
db = client.radio_database
db.radio_collection.drop()
collection = db.radio_collection

hosts = ['smart-on-sunday-with-gordon-smart',
         'x-posure-with-john-kennedy',
         'johnny-vaughan',
         'dan-oconnell',
         'jack-saunders',
         'the-chris-moyles-show',
         'toby-tarrant',
         'issy']

# hosts = ['smart-on-sunday-with-gordon-smart']

def get_url(date_number,year_in,month_in,host_in):
    return r"http://www.radiox.co.uk/playlist/"+year_in+"/"+month_in+"/"+str(date_number)+"/"+host_in+"/"

# today = datetime.datetime.now()
# month_today = today.strftime('%B').lower()
# year_today = today.year
# last_month = (today - relativedelta(months=1)).strftime('%B').lower()

base = datetime.datetime.today()
date_range_datetime = [base - datetime.timedelta(days=x) for x in range(0, 31)]
date_range = [int(x.strftime('%d')) for x in date_range_datetime]
month_range = [x.strftime('%B').lower() for x in date_range_datetime]
year_range = [x.strftime('%Y') for x in date_range_datetime]

keys = ['date', 'title', 'artist', 'artist_gender', 'song_year', 'country', 'playtime','host']


for host in hosts:
    for k in range(len(date_range)):
    # for k in range(1,2):
        print(host)
        month = month_range[k]
        day = date_range[k]
        year = year_range[k]
        my_url = get_url(day,year, month,host)
        print(my_url)
        try:
            urllib.request.urlopen(my_url)
        except (urllib.error.URLError, urllib.error.HTTPError):
            continue
        with urllib.request.urlopen(my_url) as url:
            s = url.read()
        soup = BeautifulSoup(s, 'html.parser')
        elements_track = soup.find_all(class_="track".split())
        elements_artist = soup.find_all(class_="artist".split())
        elements_playtime = soup.find_all('p', {'class':'dtstart'})
        host_raw = soup.find('div', {'class':'playlist_title'})
        host_name = host_raw.find_all('span')[0].text.strip()
        playdate = ' '.join(host_raw.find_all('h1')[0].text.strip().split(' ')[2:5])
        list_of_tracks = []
        for j in range(len(elements_track)):
            flag = 0
            try:
                if elements_track[j].a['class'][0] == 'first':
                    flag = 1
                    continue
            except (TypeError, KeyError):
                pass

            if flag == 0:
                try:
                    if elements_track[j].span['class'][0] == 'track_artist':
                        flag = 1
                        continue
                except (TypeError, KeyError):
                    pass

            if flag == 0:
                # print(flag)
                try:
                    if elements_track[j].span.string.replace('\n','').replace('  ','') != 'None':
                        list_of_tracks.append(elements_track[j].span.string.replace('\n','').replace('  ',''))
                except AttributeError:
                    try:
                        if str(elements_track[j].a.contents[0]) == '<em>Watch</em>':
                            list_of_tracks.append(elements_track[j].a.contents[1].strip())
                        else:
                            try:
                                list_of_tracks.append(elements_track[j].a.contents[0].strip())
                            except:
                                continue
                    except:
                        continue
        list_of_artists = []
        for n in range(len(elements_artist)):
            try:
                list_of_artists.append(elements_artist[n].text.strip().replace('\n','').replace('  ',''))
            except AttributeError:
                continue
        for i in range(len(list_of_artists)):
            # try:
            try:
                results = d.search(list_of_tracks[i],artist=list_of_artists[i], type='release')
                release_year = results[0].year
                release_country = results[0].country
                try:
                    artist = list_of_artists[i]
                    try:
                        page = wikipedia.page(artist)
                    except wikipedia.exceptions.DisambiguationError:
                        page = wikipedia.page(artist + ' (band)')
                    soup = BeautifulSoup(page.html(),'html.parser')
                    # origin = soup.find_all('th',string='Origin')[0].nextSibling.find_all('a')[0].text.strip()
                    # try:
                    #     members = soup.find_all('th',string='Members')
                    #     lead_singer = members[0].nextSibling.find_all('li')[0].text.strip()
                    # except IndexError:
                    try:
                        members = soup.find_all('th',string='Members')
                        lead_singer = members[0].nextSibling.find_all('a')[0].text.strip()
                    except IndexError:
                        try:
                            members = soup.find_all('th',string='Past members')
                            lead_singer = members[0].nextSibling.find_all('a')[0].text.strip()
                        except IndexError:
                            lead_singer = artist
                    lead_singer_page = wikipedia.page(lead_singer)
                    lead_singer_page_soup = BeautifulSoup(lead_singer_page.html(),'html.parser')
                    lead_singer_page_text = lead_singer_page_soup.get_text().lower()
                    male_count = len(re.findall(r'\bhe\b', lead_singer_page_text)) + len(re.findall(r'\bhis\b', lead_singer_page_text)) + len(re.findall(r'\bhim\b', lead_singer_page_text))
                    female_count = len(re.findall(r'\bshe\b', lead_singer_page_text))+ len(re.findall(r'\bhers\b', lead_singer_page_text)) + len(re.findall(r'\bher\b', lead_singer_page_text))
                    artist_gender = ['m' if male_count > female_count else 'f'][0]
                    # print('here')
                except:
                    continue

                insert_dict = dict.fromkeys(keys)
                insert_dict['date'] = playdate
                insert_dict['title'] = list_of_tracks[i]
                insert_dict['artist'] = list_of_artists[i]
                insert_dict['artist_gender'] = artist_gender
                insert_dict['song_year'] = release_year
                insert_dict['country'] = release_country
                insert_dict['playtime'] = elements_playtime[i].contents[0]
                insert_dict['host'] = host_name
                print(insert_dict)
                insert = collection.insert_one(insert_dict).inserted_id
                # insert_list = (playdate,
                #                list_of_tracks[i],
                #                list_of_artists[i],
                #                release_year,
                #                release_country,
                #                elements_playtime[i].contents[0],
                #                host_name)
                # try:
                #     cur.execute("INSERT INTO songs VALUES (?,?,?,?,?,?,?)",insert_list)
                #     # print(insert_list)
                # except sqlite3.Error as e:
                #     print("An error occurred:", e.args[0])
            except:
                continue

# con.commit()
# if con:
#     con.close()


# if __name__ == "__main__":
#     return None
