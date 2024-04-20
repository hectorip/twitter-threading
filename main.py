import os
import re
import tweepy
import yaml
import sched
import time
import datetime
import argparse

from dotenv import load_dotenv


load_dotenv()

API_KEY = os.environ["API_KEY"]
API_KEY_SECRET = os.environ["API_KEY_SECRET"]
ACCESS_TOKEN = os.environ["ACCESS_TOKEN"]
ACCESS_TOKEN_SECRET = os.environ["ACCESS_TOKEN_SECRET"]
BEARER_TOKEN = os.environ["BEARER_TOKEN"]


def authenticate_v1():
    auth = tweepy.OAuthHandler(API_KEY, API_KEY_SECRET)
    auth.set_access_token(ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
    return tweepy.API(auth, wait_on_rate_limit=True)


def authenticate():
    client = tweepy.Client(
        consumer_key=API_KEY,
        consumer_secret=API_KEY_SECRET,
        access_token=ACCESS_TOKEN,
        access_token_secret=ACCESS_TOKEN_SECRET,
    )
    return client


def load(filename):
    with open(filename) as file:
        thread = yaml.load(file, Loader=yaml.FullLoader)

    return thread["thread"]


def upload_media(api, filename):
    res = api.media_upload(filename)
    return res.media_id


def post(api, api_v1, thread):
    status = None
    for tweet in thread["tweets"]:
        print(f"Posting tweet that starts with {tweet['text'][:10]}...")
        if status:
            print(status.data)
        args = {
            "text": tweet["text"],
            "in_reply_to_tweet_id": (status.data.get("id") if status else None),
        }
        print(args)
        if "attachment" in tweet:
            status = api.create_tweet(**args, attachment_url=tweet["attachment"])
        elif "media" in tweet:
            media_ids = []
            if type(tweet["media"]) is list:
                for filename in tweet["media"]:
                    media_ids.append(upload_media(api_v1, filename))
            else:
                media_ids.append(upload_media(api_v1, tweet["media"]))
            status = api.create_tweet(**args, media_ids=media_ids)
        else:
            status = api.create_tweet(**args)


def schedule(api, api_v1, thread, when):
    when = datetime.datetime.strptime(when, "%Y-%m-%d %H:%M")
    delta = (when - datetime.datetime.now()).total_seconds()

    if delta < 0:
        raise Exception("The value of the when argument is in the past")

    schedule = sched.scheduler(time.time, time.sleep)
    schedule.enter(
        delta, 60, post, kwargs={"api": api, "api_v1": api_v1, "thread": thread}
    )
    schedule.run()


def when_format(arg_value, pat=re.compile(r"(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2})")):
    if not pat.match(arg_value):
        raise argparse.ArgumentTypeError("Invalid format. Expecting yyyy-mm-dd hh:mm")

    return arg_value


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--thread", type=str, required=True, help="The yaml file containing the thread"
    )
    parser.add_argument(
        "--when",
        type=when_format,
        required=False,
        help="The date and time when the thread will be posted",
    )
    args = parser.parse_args()

    api = authenticate()
    api_v1 = authenticate_v1()
    thread = load(args.thread)

    if not args.when:
        post(api, api_v1, thread)
    schedule(api, thread, args.when)
