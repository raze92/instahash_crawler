import requests
import json
import re
import time
from tqdm import tqdm
from bs4 import BeautifulSoup

USER_URL = 'https://www.instagram.com/'
TAG_URL = 'https://www.instagram.com/explore/tags/'
POST_URL = 'https://www.instagram.com/p/'

def get_shared_data(url: str):
    """Reads shared data from instagram sourcecode.
    
    Arguments:
        url {str} -- URL of the instagram page.
    
    Returns:
        json -- Shared data from URL.
    """

    # Get sourcecode from page
    source = requests.get(url)
    
    if source.status_code != 200:
        # ToDo Exception
        return None

    soup = BeautifulSoup(source.text, "html.parser")

    # Search for shared data and parse to json
    for item in soup.findAll('script'):
        if item.string is not None and item.string.startswith('window._sharedData'):
            content = item.string.replace("window._sharedData = ", "", 1)[:-1]
            return json.loads(content)

    # ToDo Exception if no shared data found

def get_tags_from_post(post_url: str):
    """Reads all hashtags from instagram post.
    
    Arguments:
        post_url {str} -- URL from instagram post.
    
    Returns:
        [str] -- List of used hashtags.
    """

    # Get page sourcecode 
    source = requests.get(post_url)
    soup = BeautifulSoup(source.text, "html.parser")

    # Parse all hashtags from source
    content = ""
    js = None
    for item in soup.findAll('script'):
        if item.string is not None and item.string.startswith('window._sharedData'):
            tags = re.findall(r"#[\w']+", item.string)
            return [x.lstrip('#') for x in tags]


def get_tags_from_user(user: str, num_of_posts: int = 9):
    """Reads all used hashtags from latest posts of user.
    
    Arguments:
        user {str} -- Username.
    
    Keyword Arguments:
        num_of_posts {int} -- Number of latest posts will be used. (default: {9})
    
    Returns:
        [str] -- List of used hashtags.
    """
    
    # Read shared Data
    data = get_shared_data(USER_URL + user)
    if data is None:
        print("Unable to load user " + user + "!")
        return None

    posts = data['entry_data']['ProfilePage'][0]['graphql']['user']['edge_owner_to_timeline_media']['edges']

    # Read tags of recent posts
    tags = []
    for post in posts[:num_of_posts]:
        post_tags = get_tags_from_post(POST_URL + post['node']['shortcode'])
        tags.extend(x for x in post_tags if x not in tags)

    return tags

def get_tags_from_tag(tag: str, top_posts: bool = False, num_of_posts: int = 9):
    """Reads all used hashtags from latest or top posts of tag page.
    
    Arguments:
        tag {str} -- Tag name.
    
    Keyword Arguments:
        top_posts {bool} -- If True uses the top posts instead of recent posts. (default: {False})
        num_of_posts {int} -- Number of posts will be used. (default: {9})
    
    Returns:
        [str] -- List of used hashtags.
    """

    # Read shared Data
    data = get_shared_data(TAG_URL + tag)
    if data is None:
        print("Unable to load tag " + tag + "!")
        return None
    
    # Get Posts
    posts = None
    if top_posts: # Get top posts
        posts = data['entry_data']['TagPage'][0]['graphql']['hashtag']['edge_hashtag_to_top_posts']['edges']

        if num_of_posts > 9:
            print('Warning: On top posts maximum 9 posts are possible!')
            num_of_posts = 9
    else: # Get recent posts
        posts = data['entry_data']['TagPage'][0]['graphql']['hashtag']['edge_hashtag_to_media']['edges']

    # Read tags of posts
    tags = []
    for post in posts[:num_of_posts]:
        post_tags = get_tags_from_post(POST_URL + post['node']['shortcode'])
        if post_tags is None:
            # ToDO Exception
            continue
        
        tags.extend(x for x in post_tags if x not in tags)

    return tags


def get_count_of_posts(tag: str):
    """Reads the number of posted contents with a hashtag.
    
    Arguments:
        tag {str} -- Hashtag.
    
    Returns:
        int -- Count of posts.
    """

    # Read shared Data
    data = get_shared_data(TAG_URL + tag)
    if data is None:
        # ToDO Exception
        return None

    return int(data['entry_data']['TagPage'][0]['graphql']['hashtag']['edge_hashtag_to_media']['count'])

def get_multiple_count_of_posts(tags: [str]):
    tags_counts = []
    t = tqdm(range(len(tags)))
    for i in t:
        count = get_count_of_posts(tags[i])

        sleep_time = 1
        broken = False
        while count is None:
            t.set_description('Waiting ' + str(sleep_time) + 's...')
            t.refresh()
            time.sleep(sleep_time)
            count = get_count_of_posts(tags[i])

            if count is not None:
                t.set_description('')
                t.refresh()
            else:
                sleep_time *= 2
                if sleep_time > 128:
                    broken = True
                    break

        if broken:
            print(tags[i] + " is broken")
            continue


        tags_counts.append([tags[i], count])
        time.sleep(0.5)

    return tags_counts

