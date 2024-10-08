from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from db import db
from generateContent import generateHtmlContent
from generateVideo import generateVideos
from transcript import get_transcript
app = FastAPI()


origins = [
    "http://localhost:3000",  # Example: Your frontend on localhost
    "https://sarfaraj.site",  # Example: Your production frontend
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Allows specific origins
    allow_credentials=True,  # Allows cookies to be included in requests
    allow_methods=["*"],  # Allows all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],  # Allows all headers
)


@app.get("/htmlcontent/{videoId}")
def html_content(videoId: str):

    print(videoId)
    if not videoId:
        return HTTPException(status_code=400, detail="Topic missing")
    data = db["html_content"].find({'videoId': videoId}, {'_id': 0})

    return list(data)

@app.get('/transcript/{videoId}')
def get_transcript_api(videoId:str):
    try:
        return get_transcript(videoId)
    except Exception as e:
        # print(e)
        return {"error": str(e)}
@app.post("/generatehtmlcontent")
def generate_html_content(body: dict):
    topic = body.get("topic")
    videoId = body.get("videoId")

    print(topic,videoId)
    if not topic or not videoId:
        raise HTTPException(status_code=400, detail="Topic missing")

    video = db["videos"].find_one({'videoId': videoId})
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    content =  [content for content in video["concept"] if content.get('concept description') == topic or content.get('description') == topic]

    if len(content) == 0:
        print("Content not found")
        raise HTTPException(status_code=404, detail="Content not found")
    

    html_content = generateHtmlContent(topic=topic).strip()

    db["html_content"].insert_one({
        "topic": topic,
        "videoId": videoId,
        "html_content": html_content
    })
    return {
        "topic": topic,
        "videoId": videoId,
        "html_content": html_content
    }
    


@app.get("/video/{videoId}")
def get_video(videoId: str):
    print(videoId)
    
    data = db["videos"].find_one({'videoId': videoId}, {"transcript": 0, '_id': 0})

    if not data:
        return HTTPException(status_code=404, detail="Video not found")
    return data


@app.get("/videos/{subject}")
def get_videos(subject: str):
    print(subject)
    if not subject:
        return HTTPException(status_code=400, detail="Subject missing")
    data = db["videos"].find({'topic': subject}, {"transcript": 0, '_id': 0})
    data = list(data)



    return {
            "videos": data
        }


@app.post("/generatevideo")
def generate_video(body:dict):
    try:
        subject=body.get('subject')
        if not subject:
            return HTTPException(status_code=400, detail="Subject missing")

        subjectData = db["subject"].find_one({"fields": subject})

        if not subjectData:
            return HTTPException(status_code=400, detail="Invalid topic")

        course_name = subjectData.get("name") or ""

        next_page_token_data = db["page_token"].find_one({"subject":subject})

        if next_page_token_data:
            next_page_token = next_page_token_data['token']
        else:
            next_page_token=None
        query = f'"{subject}" AND "{course_name}" AND ("tutorial" OR "lesson" OR "lecture" OR "Explained" OR "one shot" OR "chapter" OR "learn")'
        generatedData = generateVideos(query,4,next_page_token,course_name)
        if not generatedData:
            return HTTPException(status_code=400, detail="Rate limit exists, please try again later")
        

        videos = generatedData.get('videos')
        next_page_token = generatedData.get("nextPageToken")

        if len(videos)==0:
            return HTTPException(status_code=500, detail="Could not generate video")




        db['page_token'].update_one({'subject':subject},{'$set':{'token':next_page_token}},True)

        ids = [video['videoId'] for video in videos]
        existing_videos = db["videos"].find({'videoId': {'$in': ids}}, {'videoId': 1})
        existing_videos = [video['videoId'] for video in existing_videos]
        
        filtered_videos = [video for video in videos if video['videoId'] not in existing_videos]

        for v in filtered_videos:
            v['topic'] = subject
            v['subject'] = course_name

        db["videos"].insert_many(filtered_videos)
            

        videos = list(filtered_videos)
        for item in videos:
            if "_id" in item:
                del item["_id"] 

            if "transcript" in item:
                del item["transcript"]



        print("Number of videos generated", len(videos))

        return {
            "videos": videos,
        }
    except Exception as e:
        print(e)
        return {"error": str(e)}


@app.get("/subjects")
def get_subjects():
    data = db["subject"].find({}, {"_id": 0})

    data = list(data)
    return {
        "subjects": data
    }







# Run the application
if __name__ == '__main__':
    import uvicorn
    # uvicorn.run(app)
    uvicorn.run(app,host="0.0.0.0",port=80)


