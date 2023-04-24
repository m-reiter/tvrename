#!/home/reiter/venvs/tvdb/bin/python3

import sys
import tvdb_api
import argparse

from pathlib import Path
from collections import defaultdict
from fuzzywuzzy import fuzz

API_KEY_FILE = Path.home() / ".tvdb_api_key"
LANGUAGE = "de"

def get_args():

    parser = argparse.ArgumentParser(description="Rename TV show episodes based on episode names by looking up season and episode numbers on TVDB.")
    parser.add_argument("-s","--show", help="Set show name to argument instead of trying to parse from file or directory name.")
    parser.add_argument("-d","--dry-run", action="store_true", help="Dry run. Don't actually rename files.")
    parser.add_argument("-i","--ask", action="store_true", help="Ask before actually renaming files.")
    parser.add_argument("-S","--separator", default=" - ", help="String that separates show name from episode name (defaults to \"%(default)s\").")
    parser.add_argument("-l","--language", default=LANGUAGE, help="Language to search on TVDB (defaults to \"%(default)s\").")
    parser.add_argument("files", nargs="+", metavar="FILE", help="The files to process.")

    args = parser.parse_args()

    if args.dry_run:
        print("*** Dry run only ***")
        
    return args

def get_episodes(args):

    shows_to_episodes = defaultdict(list)

    for file in args.files:
        path = Path(file)
        if not path.is_file():
            print(f"{file} is not a regular file, skipping.")
            continue
        if args.show:
            show = args.show
            episodename = path.stem
        elif args.separator in path.stem:
            show, episodename = path.stem.split(args.separator,1)
        else:
            show = path.parent.name.replace("_"," ")
            episodename = path.stem
        shows_to_episodes[show].append((episodename,path))

    return shows_to_episodes

def query_and_rename(shows_to_episodes,args):

    apikey = API_KEY_FILE.read_text().strip()

    tvdb = tvdb_api.Tvdb(apikey=apikey,language=args.language)

    for show, episodes in shows_to_episodes.items():
        
        show_info = tvdb[show]
        show_name = show_info.__dict__["data"]["seriesName"]
        all_episodes = [ (e['episodeName'],e['airedSeason'],e['airedEpisodeNumber']) for season in show_info.values() for e in season.values() ]

        for episodename,path in episodes:
            scores = { e: fuzz.partial_ratio(episodename, e[0]) for e in all_episodes }
            hits = [ episode for episode,score in scores.items() if score == max(scores.values()) ]
            if not hits:
                print(f"No candidates found for {path.name}, skipping.")
                continue
            elif len(hits) == 1:
                index = 0
            else:
                print(f"Found multiple candidates for {path.name}:")
                for i,e in enumerate(hits):
                    print(f"{i}) S{e[1]:02d}E{e[2]:02d}: {e[0]}")
                while True:
                    answer = input(f"   Choose correct episode (0-{len(hits)-1}/skip/abort)? ")
                    if "abort".startswith(answer):
                        return
                    if "skip".startswith(answer):
                        skip = True
                        break
                    try:
                        index = int(answer)
                        if index in range(len(hits)):
                            skip = False
                            break
                    except ValueError:
                        pass
                if skip:
                    continue
            new_name = "{} - S{:02d}E{:02d} - {}{}".format(show_name,hits[index][1],hits[index][2],hits[index][0],path.suffix)
            new_name = new_name.replace("/","\u2044")
            new_path = path.with_name(new_name)
            if new_path == path:
                print(f'"{path.name}" is already named correctly, skipping.')
            elif new_path.exists():
                print(f'"{new_path.name}" already exists, skipping.')
            else:
                print(f'"{path.name}" -> "{new_name}"')
                if args.dry_run:
                    continue
                if args.ask:
                    while True:
                        answer = input("    Rename (yes/no/abort)? ")
                        if "yes".startswith(answer):
                            rename = True
                            break
                        if "no".startswith(answer):
                            rename = False
                            break
                        if "abort".startswith(answer):
                            return
                    if not rename:
                        continue
                path.rename(new_path)

def main():

    args = get_args()

    shows_to_episodes = get_episodes(args)

    query_and_rename(shows_to_episodes,args)

if __name__ == "__main__":
    main()
