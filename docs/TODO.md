# TODO

## 2026-05-01

- FINALIZE NAME OF PROJECT. Rename FOLDERs, DOCKER, DOCKER COMPOSE, CONFIG.yaml. Update VERSION.md with note of change

- When reading back the response, if it's long, the reponse ends up "behind" the mic button. Not sure how to hide/slide/move it.

- Work on mouth animation maybe. Increase speed or change in amplitude.

- Add Calendar API to read calendar events for summaries

- RAG - can we get it to read additional information. Might be better just for a chat based program and take out the TTS/SST.

- If it's a new day (need to store current date) on start up, start a new conversation? Maybe? Maybe not on second thought.


## PROMPTS:

Add Calendar:
For my next big update, version 1.2, I would like to add the ability to query an Outlook.com or Gmail Calendar with maybe an App Secret or API key for the call? I would like my assistant to be able to understand my schdedule or ask questions about it. I would want this integration to be configured in the yaml file, where I could specify a prodiver and whatever authentication i would need.

Add RAG or Text repo:
The next big update I want to make would be a way for the agent to query or reference old chat, or even better a directory of .TXT, .MD, or .PDF files. Essenitally I think a RAG type solution with some embeddings? Not sure if I am using the correct terms there. I want to give it a 'knowledge base' to suppliment it's existing knowledge. Would it also be possible to have it load and merge old chats? Or is that not a good design pattern for something like this? Is is better to keep chats seperate, and suppliment long term knowledge with a RAG solution?