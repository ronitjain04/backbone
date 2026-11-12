// Context is request-local and kept in browser memory separately for each course.
export const MAX_HISTORY_MESSAGES=8;
export const MAX_HISTORY_MESSAGE_CHARS=4000;
export const MAX_HISTORY_CHARS=16000;
export const MAX_REQUEST_BYTES=128*1024;

export function normalizeHistory(history=[]){
 if(!Array.isArray(history)||history.length>MAX_HISTORY_MESSAGES||history.length%2)throw Error('Invalid conversation history');
 let total=0;
 const messages=history.map((message,index)=>{
  if(!message||typeof message!=='object'||Array.isArray(message)||Object.keys(message).some(key=>key!=='role'&&key!=='content'))throw Error('Invalid conversation message');
  if(message.role!==(index%2?'assistant':'user')||typeof message.content!=='string'||!message.content.trim()||message.content.length>MAX_HISTORY_MESSAGE_CHARS)throw Error('Invalid conversation message');
  const content=message.content.trim();total+=content.length;
  return {role:message.role,content};
 });
 if(total>MAX_HISTORY_CHARS)throw Error('Conversation history is too large');
 return messages;
}

function boundedContent(text){
 text=text.trim();
 if(text.length<=MAX_HISTORY_MESSAGE_CHARS)return text;
 const suffix='\n[Earlier message truncated.]';
 let head=text.slice(0,MAX_HISTORY_MESSAGE_CHARS-suffix.length);
 // Do not split the two UTF-16 code units of an emoji at the truncation boundary.
 if(/[\uD800-\uDBFF]$/.test(head))head=head.slice(0,-1);
 return head+suffix;
}

export function appendExchange(history,query,answer){
 const messages=[...normalizeHistory(history),{role:'user',content:boundedContent(query)},{role:'assistant',content:boundedContent(answer)}].slice(-MAX_HISTORY_MESSAGES);
 while(messages.reduce((n,message)=>n+message.content.length,0)>MAX_HISTORY_CHARS)messages.splice(0,2);
 return messages;
}
