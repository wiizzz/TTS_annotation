import pandas as pd
import os

split = [1,2,3]
for s in split:
    root = f"/Users/jeff/Downloads/check_csv/Adv/part{s}"
    files = os.listdir(root)
    for f in files:
        worker_df = pd.read_csv(os.path.join(root, f))
        ans_df = pd.read_csv(f'/Users/jeff/Downloads/check_csv/answer/task1_adv/adv{s}.csv')

        check_rows = worker_df[worker_df['Input.audio_url'].str.contains(
            'https://huggingface.co/datasets/wizzzzzzzzz/TTS_annotation_check/resolve/main/Task1_Adv_Degree/audios',
            na=False  # avoids error if there are NaNs
        )]

        #print(check_rows[['Answer.perceived_emotion.label', 'Input.audio_url']])
        dic = {}
        for emo, url in zip(check_rows['Answer.emotion_intensity.label'], check_rows['Input.audio_url']):
            _, name = os.path.split(url)
            dic[name] = emo

        ans = {}
        for emo, name in zip(ans_df['EmoInt'], ans_df['FileName']):
            ans[name] = emo
        if dic == {}:
            print(f"split{s} {f}: N/A")
            continue
        c = 0
        i = 0
        for k in dic:
            i += 1
            #print(ans[k], dic[k])
                #print(k, ans[k], dic[k])
            if ans[k] == "Hi" and ("4" in dic[k] or "5" in dic[k]):
                c += 1
            elif ans[k] == "Low" and ("1" in dic[k] or "2" in dic[k]):
                c += 1
        print(f"split{s} {f}: {c}/{i} = {c/i*100}%")
    print()
