
/****************************************************
 * 假資料：追蹤中清單
 ****************************************************/
const followData = [
  {name:"Butter", avatar:"https://i.pravatar.cc/24?img=1"},
  {name:"Peanut", avatar:"https://i.pravatar.cc/24?img=5"},
  {name:"小黑", avatar:"https://i.pravatar.cc/24?img=8"},
  {name:"逗逗", avatar:"https://i.pravatar.cc/24?img=10"},
];

/****************************************************
 * 假資料：貼文
 ****************************************************/
const postData = [
  {
    id:'p1',
    user:{name:'逗逗', avatar:'https://i.pravatar.cc/80?img=10'},
    ts:'2小時前',
    text:'噢噢，逗逗啃寵物骨頭的模樣好可愛 🐶',
    type:'single',
    media:['images/1080.webp'],
    likes:20,
    comments:[
      {id:'c1', user:{name:'Lydia', avatar:'https://i.pravatar.cc/40?img=12'}, text:'這張真的太可愛了😍', likes:3, replies:[{id:'c1r1',user:{name:'逗逗',avatar:'https://i.pravatar.cc/40?img=10'},text:'謝謝妳～牠超會吃😂',likes:1}]},
      {id:'c2', user:{name:'Jay', avatar:'https://i.pravatar.cc/40?img=16'}, text:'也太療癒了吧~', likes:1, replies:[]},
    ],
    repostFrom:null,
  },
  {
    id:'p2',
    user:{name:'Butter', avatar:'https://i.pravatar.cc/80?img=1'},
    ts:'昨天',
    text:'戶外散步集錦，一次放上四張～',
    type:'carousel',
    media:[
      'images/200427-23094-01-Cuuu5.jpg',
      'images/original.jpg',
      'images/1382490545-442951735.jpg',
      'images/southeast.jpg'
    ],
    likes:12,
    comments:[
      {id:'c3', user:{name:'MEI', avatar:'https://i.pravatar.cc/40?img=22'}, text:'路邊花也美！', likes:0, replies:[]},
    ],
    repostFrom:null,
  },
  {
    id:'p3',
    user:{name:'小黑', avatar:'https://i.pravatar.cc/80?img=8'},
    ts:'3天前',
    text:'小黑今天去洗澡啦🛁',
    type:'carousel',
    media:[
      'images/a5139e2a-54d9-427a-982a-a898c7d69034.png',
      'images/6da1c8d2-5e89-4680-8e60-b1c8302ac816.png',
      'images/d01badcf-644d-48de-837e-d6b9c7fe4ac8.png'
    ],
    likes:5,
    comments:[],
    repostFrom:'p1'
  }
];

/****************************************************
 * 分享渠道設定（含 Instagram）
 ****************************************************/
const shareChannels = [
  { id: 'line',   label: 'LINE' },
  { id: 'fb',     label: 'Facebook' },
  { id: 'x',      label: 'X (Twitter)' },
  { id: 'ig',     label: 'Instagram' }, // 直接開啟 instagram.com
  { id: 'email',  label: 'Email' },
  { id: 'copy',   label: '複製連結' },
  { id: 'system', label: '系統分享' }, // 使用 Web Share API
];

const shareOverlay    = document.getElementById('shareOverlay');
const sharePreviewImg = document.getElementById('sharePreviewImg');
const shareChannelsEl = document.getElementById('shareChannels');
const shareCloseBtn   = document.getElementById('shareClose');
let sharePostId=null;

function openShareModal(post){
  sharePostId = post.id;
  sharePreviewImg.src = post.media?.[0] || '';
  shareOverlay.classList.add('active');
  shareOverlay.setAttribute('aria-hidden','false');
}
function closeShareModal(){
  sharePostId=null;
  shareOverlay.classList.remove('active');
  shareOverlay.setAttribute('aria-hidden','true');
}
shareCloseBtn.addEventListener('click',closeShareModal);
shareOverlay.addEventListener('click',e=>{if(e.target===shareOverlay)closeShareModal();});

function renderShareChannels(){
  shareChannelsEl.innerHTML='';
  shareChannels.forEach(ch=>{
    const b=document.createElement('button');
    b.textContent=ch.label;
    b.dataset.channel = ch.id;
    b.addEventListener('click', onShareChannelClick);
    shareChannelsEl.appendChild(b);
  });
}

/****************************************************
 * 分享輔助
 ****************************************************/
function getSharePayload(post){
  const url  = `${location.origin}${location.pathname}#${post.id}`;
  const text = `${post.user.name}: ${post.text}`.trim();
  const title = '毛孩社群平台';
  return { title, text, url };
}

function openWithFallback(appUrl, webUrl){
  const timer = setTimeout(()=> {
    if (webUrl) window.open(webUrl, '_blank', 'noopener');
  }, 1200);
  window.location.href = appUrl;
}

async function shareViaWebAPI(payload){
  try{
    if (navigator.share) {
      await navigator.share({ title: payload.title, text: payload.text, url: payload.url });
      closeShareModal();
      return true;
    }
  }catch(e){}
  return false;
}

function onShareChannelClick(e){
  const channel = e.currentTarget.dataset.channel;
  const post = postData.find(p => p.id === sharePostId);
  if (!post) return;

  const { title, text, url } = getSharePayload(post);

  if (channel === 'system') {
    shareViaWebAPI({ title, text, url });
    return;
  }

  switch(channel){
    case 'line': {
      const msg = encodeURIComponent(`${text} ${url}`);
      const appUrl = `line://msg/text/${msg}`;
      const webUrl = `https://line.me/R/msg/text/?${msg}`;
      openWithFallback(appUrl, webUrl);
      break;
    }
    case 'fb': {
      const shareUrl = `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(url)}`;
      window.open(shareUrl, '_blank', 'noopener');
      break;
    }
    case 'x': {
      const shareUrl = `https://twitter.com/intent/tweet?text=${encodeURIComponent(text)}&url=${encodeURIComponent(url)}`;
      window.open(shareUrl, '_blank', 'noopener');
      break;
    }
    case 'ig': {
      // 無法帶內容，直接開啟 Instagram 網站（或可能喚起 App）
      window.open('https://www.instagram.com/', '_blank', 'noopener');
      break;
    }
    case 'email': {
      const subject = encodeURIComponent(title);
      const body = encodeURIComponent(`${text}\n\n${url}`);
      const mailto = `mailto:?subject=${subject}&body=${body}`;
      window.location.href = mailto;
      break;
    }
    case 'copy': {
      const toCopy = `${text} ${url}`.trim();
      if (navigator.clipboard?.writeText) {
        navigator.clipboard.writeText(toCopy).then(()=>{
          alert('已複製連結！');
          closeShareModal();
        }, ()=>{ fallbackCopy(toCopy); });
      } else {
        fallbackCopy(toCopy);
      }
      break;
    }
    default: {
      shareViaWebAPI({ title, text, url }) || alert('此分享目標不支援，請使用系統分享。');
    }
  }
}

function fallbackCopy(text){
  const ta = document.createElement('textarea');
  ta.value = text;
  ta.style.position = 'fixed';
  ta.style.opacity = '0';
  document.body.appendChild(ta);
  ta.select();
  try { document.execCommand('copy'); alert('已複製連結！'); }
  catch { alert('複製失敗'); }
  document.body.removeChild(ta);
  closeShareModal();
}

/****************************************************
 * 渲染與互動（其餘功能維持原樣）
 ****************************************************/
function renderFollowList(){
  const ul = document.getElementById('followList');
  ul.innerHTML = '';
  followData.forEach(f=>{
    const li = document.createElement('li');
    li.innerHTML = `<img src="${f.avatar}" alt="${f.name}"><span class="name">${f.name}</span>`;
    ul.appendChild(li);
  });
}

function commentHtml(c,isReply){
  return `<div class="comment-item" data-commentid="${c.id}">
    <img src="${c.user.avatar}" alt="${c.user.name}">
    <div class="comment-bubble">
      <div class="comment-author">${c.user.name}</div>
      <div class="comment-text">${c.text}</div>
      <div class="comment-footer">
        <button class="comment-like" aria-label="like comment">👍 <span class="comment-like-count">${c.likes}</span></button>
        ${!isReply?'<button class="comment-reply">回覆</button>':''}
      </div>
    </div>
  </div>`;
}

function createPostCard(p){
  const card = document.createElement('article');
  card.className='post-card';
  card.dataset.postid = p.id;

  let repostHtml='';
  if(p.repostFrom){
    const srcPost = postData.find(x=>x.id===p.repostFrom);
    if(srcPost){
      repostHtml = `<div class="repost-info">↻ 轉發自 ${srcPost.user.name}</div>`;
    }
  }

  let mediaHtml='';
  if(p.type==='single'){
    mediaHtml=`<div class="post-media-single"><img src="${p.media[0]}" alt="貼文圖片"></div>`;
  }else{
    const imgs=p.media.map(url=>`<img src="${url}" alt="carousel-img">`).join('');
    const ind=p.media.map((_,i)=>`<button data-idx="${i}" aria-label="移動到第${i+1}張"></button>`).join('');
    mediaHtml=`<div class="carousel-wrapper" data-count="${p.media.length}">
      <div class="carousel-track">${imgs}</div>
      <button class="carousel-btn prev" aria-label="上一張">◀</button>
      <button class="carousel-btn next" aria-label="下一張">▶</button>
      <div class="carousel-indicators">${ind}</div>
    </div>`;
  }

  const commentsHtml = p.comments.map(c=>{
    const repliesHtml = c.replies.map(r=>commentHtml(r,true)).join('');
    return commentHtml(c,false)+`<div class="reply-thread">${repliesHtml}</div>`;
  }).join('');

  card.innerHTML=`
    <div class="post-header">
      <img class="avatar" src="${p.user.avatar}" alt="${p.user.name}">
      <div class="post-user-info">
        <span class="post-username">${p.user.name}</span>
        <span class="post-timestamp">${p.ts}</span>
      </div>
    </div>
    ${repostHtml}
    <div class="post-text">${p.text}</div>
    ${mediaHtml}
    <div class="post-actions">
      <button class="btn-like" aria-label="like"><span class="icon">🖤</span><span class="like-count">${p.likes}</span></button>
      <button class="btn-comment" aria-label="comment">💬 留言</button>
      <button class="btn-share" aria-label="share">🔗 分享</button>
      <button class="btn-repost" aria-label="repost">↻ 轉發</button>
    </div>
    <div class="comments-wrapper">
      ${commentsHtml}
      <div class="add-comment">
        <input type="text" placeholder="輸入留言…" aria-label="add comment" />
        <button class="send">送出</button>
      </div>
    </div>
  `;

  if(p.type==='carousel') initCarousel(card);

  return card;
}

function renderFeed(){
  const feedEl = document.getElementById('feed');
  feedEl.innerHTML='';
  postData.forEach(p=>feedEl.appendChild(createPostCard(p)));
}

function togglePostLike(btn){
  const postCard = btn.closest('.post-card');
  const postid = postCard.dataset.postid;
  const post = postData.find(p=>p.id===postid);
  if(!post) return;
  const countEl = btn.querySelector('.like-count');
  const iconEl = btn.querySelector('.icon');
  const hearted = btn.classList.toggle('hearted');
  if(hearted){
    post.likes++;
    iconEl.textContent='❤️';
  }else{
    post.likes = Math.max(0,post.likes-1);
    iconEl.textContent='🖤';
  }
  countEl.textContent=post.likes;
}

function toggleCommentLike(btn){
  const commentItem = btn.closest('.comment-item');
  const postCard = btn.closest('.post-card');
  const post = postData.find(p=>p.id===postCard.dataset.postid);
  if(!post) return;
  const cid = commentItem.dataset.commentid;
  let comment = null;
  for(const c of post.comments){
    if(c.id===cid){comment=c;break;}
    const r = c.replies.find(x=>x.id===cid);
    if(r){comment=r;break;}
  }
  if(!comment) return;
  const countEl = btn.querySelector('.comment-like-count');
  const liked = btn.classList.toggle('liked');
  comment.likes = Math.max(0, comment.likes + (liked?1:-1));
  countEl.textContent=comment.likes;
}

function addComment(postCard,inputEl,isReplyTo){
  const txt = inputEl.value.trim();
  if(!txt) return;
  const post = postData.find(p=>p.id===postCard.dataset.postid);
  if(!post) return;
  const newC = {id:'c'+Date.now(),user:{name:'我',avatar:'https://i.pravatar.cc/40?u=me'},text:txt,likes:0,replies:[]};
  if(isReplyTo){
    const target = post.comments.find(c=>c.id===isReplyTo);
    if(target) target.replies.push(newC);
  }else{
    post.comments.push(newC);
  }
  renderFeed();
}

function startReply(btn){
  const commentItem = btn.closest('.comment-item');
  const postCard = btn.closest('.post-card');
  const cid = commentItem.dataset.commentid;
  const inputEl = postCard.querySelector('.add-comment input');
  inputEl.placeholder = '回覆…';
  inputEl.focus();
  inputEl.dataset.replyTo = cid;
}

document.addEventListener('click',function(e){
  const likeBtn = e.target.closest('.post-actions .btn-like');
  if(likeBtn){togglePostLike(likeBtn);return;}

  const commentBtn = e.target.closest('.post-actions .btn-comment');
  if(commentBtn){
    const postCard = commentBtn.closest('.post-card');
    postCard.querySelector('.add-comment input').focus();
    return;
  }

  const shareBtn = e.target.closest('.post-actions .btn-share');
  if(shareBtn){
    const postCard = shareBtn.closest('.post-card');
    const post = postData.find(p=>p.id===postCard.dataset.postid);
    if(post) openShareModal(post);
    return;
  }

  const repostBtn = e.target.closest('.post-actions .btn-repost');
  if(repostBtn){
    const postCard = repostBtn.closest('.post-card');
    const post = postData.find(p=>p.id===postCard.dataset.postid);
    if(post) repost(post);
    return;
  }

  const cLikeBtn = e.target.closest('.comment-footer .comment-like');
  if(cLikeBtn){toggleCommentLike(cLikeBtn);return;}

  const replyBtn = e.target.closest('.comment-footer .comment-reply');
  if(replyBtn){startReply(replyBtn);return;}

  const sendBtn = e.target.closest('.add-comment .send');
  if(sendBtn){
    const postCard = sendBtn.closest('.post-card');
    const inputEl = postCard.querySelector('.add-comment input');
    const replyTo = inputEl.dataset.replyTo;
    addComment(postCard,inputEl,replyTo);
    inputEl.value='';
    inputEl.placeholder='輸入留言…';
    delete inputEl.dataset.replyTo;
    return;
  }
});

function initCarousel(card){
  const wrap = card.querySelector('.carousel-wrapper');
  if(!wrap) return;
  const track = wrap.querySelector('.carousel-track');
  const prevBtn = wrap.querySelector('.carousel-btn.prev');
  const nextBtn = wrap.querySelector('.carousel-btn.next');
  const dots = Array.from(wrap.querySelectorAll('.carousel-indicators button'));
  let idx=0;
  function update(){
    track.style.transform=`translateX(-${idx*100}%)`;
    dots.forEach((d,i)=>d.classList.toggle('active',i===idx));
  }
  prevBtn.addEventListener('click',()=>{idx=(idx-1+dots.length)%dots.length;update();});
  nextBtn.addEventListener('click',()=>{idx=(idx+1)%dots.length;update();});
  dots.forEach((d,i)=>d.addEventListener('click',()=>{idx=i;update();}));
  update();
}

/****************************************************
 * 啟動
 ****************************************************/
function repost(post){
  const newPost = {
    id:'rp'+Date.now(),
    user:{name:'我', avatar:'https://i.pravatar.cc/80?u=me'},
    ts:'剛剛',
    text:post.text,
    type:post.type,
    media:post.media.slice(),
    likes:0,
    comments:[],
    repostFrom:post.id,
  };
  postData.unshift(newPost);
  renderFeed();
  window.scrollTo({top:0,behavior:'smooth'});
}

renderFollowList();
renderShareChannels();
renderFeed();
