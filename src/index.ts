import env_types from "../.env.d";
import dotenv from "dotenv";
dotenv.config();
import yargs from "yargs";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
dayjs.extend(utc);

import path from "path";
import fs from "fs/promises";

import TwitterApi, { TweetUserTimelineV2Paginator, TweetV2UserTimelineParams, UsersV2Params, UserV2, UserV2Result } from "twitter-api-v2";

// Get BEARER_TOKEN
const env = process.env as NodeJS.ProcessEnv & env_types;
// Check of its existence
const { BEARER_TOKEN } = env;
if (!BEARER_TOKEN)
    throw new Error("Bearer token not provided")


const client = new TwitterApi(BEARER_TOKEN).readOnly.v2;

class User {
    rawResponse: Readonly<UserV2Result> | null = null;
    
    async getByUsername(username: string, options: Partial<UsersV2Params> = {}): Promise<UserV2Result> {
        const res = await client.userByUsername(username, options);

        this.rawResponse = res;

        if (res.errors)
            throw new Error("An error has occurred when getting user by username.");

        return res;
    }
}

class Tweets {
    id: string;
    response: TweetUserTimelineV2Paginator | null = null;
    constructor(id: string) {
        this.id = id;
    }
    
    async getTweets(options: Partial<TweetV2UserTimelineParams>): Promise<TweetUserTimelineV2Paginator> {
        const res = await client.userTimeline(this.id, options);

        if (res.errors.length)
            throw { message: "An error occurred when trying to get a user's timeline", error: res.errors };

        this.response = res;

        return res;
    }
    async downloadUntil(until: number | dayjs.Dayjs, options?: Partial<TweetV2UserTimelineParams>) {
        const limit = typeof until === "number" ? "number" : "date"
    }
}

(async () => {
    const parser = yargs(process.argv.slice(2)).options({
        
    });
    const argv = await parser.argv;

    // OPTIONS -> MOVE TO PARSER ONCE DONE
    const username = "nullluvsu";
    const max_results = 100;
    const out_path = `./data/out-${username}_3.json`;
    const save_raw = false; // Default false btw
    const raw_out = "./test.out.json";
    // const include_retweets = true;
    const start_time = dayjs().subtract(1.5, "month").utc().format();

    const user = new User();
    const p = await user.getByUsername(username, { "user.fields": ["protected", "public_metrics"] });
    if (p.data.protected)
        return console.log("Tweets are protected. Exiting.");

    const tweets = new Tweets(p.data.id);
    const t = await tweets.getTweets({ 
        max_results,
        since_id: "1514120256268419072",
        // start_time,
        "tweet.fields": [
            "source",
            "referenced_tweets",
            "public_metrics",
            "created_at"
        ],
    });

    let backup_counter = 0;
    while (t.data.meta.next_token && backup_counter < 3200) {
        console.log("Tick", backup_counter);

        await t.fetchNext();
        backup_counter += max_results;
    }

    await fs.writeFile(path.resolve(out_path), JSON.stringify(t.data, null, 4), { encoding: "utf-8" });
    console.log("Done");

    if (save_raw)
        await fs.writeFile(path.resolve(raw_out), JSON.stringify(t.data, null, 4), { encoding: "utf-8" });
})();