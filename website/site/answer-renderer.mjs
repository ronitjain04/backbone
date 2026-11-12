import MarkdownIt from 'markdown-it';
import texmath from 'markdown-it-texmath';
import katex from 'katex';
import hljs from 'highlight.js/lib/core';
import c from 'highlight.js/lib/languages/c';
import cpp from 'highlight.js/lib/languages/cpp';
import createDOMPurify from 'dompurify';

hljs.registerLanguage('c',c);
hljs.registerLanguage('cpp',cpp);
hljs.registerLanguage('lc3',()=>({
 name:'LC-3',case_insensitive:true,
 contains:[
  hljs.COMMENT(';','$'),hljs.QUOTE_STRING_MODE,
  {scope:'meta',match:/\.(?:ORIG|END|FILL|BLKW|STRINGZ)\b/},
  {scope:'keyword',match:/\b(?:ADD|AND|NOT|BR[nzp]*|JMP|JSRR?|RET|RTI|LDI?|LDR|LEA|STI?|STR|TRAP|HALT|GETC|OUT|PUTSP?|IN)\b/},
  {scope:'built_in',match:/\bR[0-7]\b/},
  {scope:'number',match:/#[+-]?\d+|\b[xX][0-9a-fA-F]+\b|\b[bB][01]+\b/}
 ]
}));

const languages={c:['c','C'],cpp:['cpp','C++'],'c++':['cpp','C++'],lc3:['lc3','LC-3'],'lc-3':['lc3','LC-3'],asm:['lc3','Assembly'],assembly:['lc3','Assembly']};
const md=new MarkdownIt({html:false,linkify:false,typographer:false,breaks:false});
md.use(texmath,{engine:katex,delimiters:['dollars','brackets'],katexOptions:{trust:false,throwOnError:false,maxExpand:1000,maxSize:10,strict:'ignore'}});
md.renderer.rules.fence=(tokens,index)=>{
 const token=tokens[index],name=token.info.trim().split(/\s+/)[0].toLowerCase();
 const [language,label]=Object.hasOwn(languages,name)?languages[name]:['plaintext','Code'];
 let code=md.utils.escapeHtml(token.content);
 if(language!=='plaintext'){
  try{code=hljs.highlight(token.content,{language,ignoreIllegals:true}).value}catch{/* Keep escaped plain code if highlighting fails. */}
 }
 return `<div class="code-block"><div class="code-language">${label}</div><pre><code class="hljs language-${language}">${code}</code></pre></div>\n`;
};
md.renderer.rules.image=(tokens,index)=>md.utils.escapeHtml(tokens[index].content);
md.renderer.rules.table_open=()=>'<div class="answer-table"><table>\n';
md.renderer.rules.table_close=()=>'</table></div>\n';
const openLink=md.renderer.rules.link_open||((tokens,index,options,env,renderer)=>renderer.renderToken(tokens,index,options));
md.renderer.rules.link_open=(tokens,index,options,env,renderer)=>{
 tokens[index].attrSet('target','_blank');
 tokens[index].attrSet('rel','noopener noreferrer');
 return openLink(tokens,index,options,env,renderer);
};
const sanitizers=new WeakMap();

export function renderAnswer(text,doc=document){
 let purifier=sanitizers.get(doc);
 if(!purifier){purifier=createDOMPurify(doc.defaultView);sanitizers.set(doc,purifier)}
 const body=doc.createElement('div');body.className='answer-body';
 body.innerHTML=purifier.sanitize(md.render(text),{USE_PROFILES:{html:true,mathMl:true,svg:true},ADD_ATTR:['target'],FORBID_TAGS:['img','iframe','object','embed','style']});
 return body;
}
