/****************************************************
 * 假資料：追蹤中清單（維持原本）
 ****************************************************/
const followData = [
  {name:"Butter", avatar:"https://i.pravatar.cc/24?img=1"},
  {name:"Peanut", avatar:"https://i.pravatar.cc/24?img=5"},
  {name:"小黑",   avatar:"https://i.pravatar.cc/24?img=8"},
  {name:"逗逗",   avatar:"https://i.pravatar.cc/24?img=10"},
];

/****************************************************
 * 假資料：首頁貼文（維持原本）
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
 * 個人主頁的貼文資料（只在 #/user/名字 時使用）
 * 每位 5~6 則，其中 1~2 則為影片
 ****************************************************/
const profilePosts = [
  /* 逗逗 */
  { id:'d1', user:{name:'逗逗', avatar:'https://i.pravatar.cc/80?img=10'}, ts:'1小時前', text:'今天跑跑！', type:'video', media:['https://interactive-examples.mdn.mozilla.net/media/cc0-videos/flower.mp4'], likes:18, comments:[] },
  { id:'d2', user:{name:'逗逗', avatar:'https://i.pravatar.cc/80?img=10'}, ts:'昨天', text:'最愛的骨頭🦴', type:'single', media:['images/1080.webp'], likes:22, comments:[] },
  { id:'d3', user:{name:'逗逗', avatar:'https://i.pravatar.cc/80?img=10'}, ts:'2天前', text:'散步遇到朋友', type:'carousel', media:['images/ChatGPT Image12_53_59.PNG','images/ChatGPT Image12_54_01.PNG'], likes:9, comments:[] },
  { id:'d4', user:{name:'逗逗', avatar:'https://i.pravatar.cc/80?img=10'}, ts:'4天前', text:'睡回籠覺', type:'single', media:['images/ChatGPT Image12_01_08.PNG'], likes:6, comments:[] },
  { id:'d5', user:{name:'逗逗', avatar:'https://i.pravatar.cc/80?img=10'}, ts:'6天前', text:'握手新技能', type:'video', media:['https://interactive-examples.mdn.mozilla.net/media/cc0-videos/flower.mp4'], likes:13, comments:[] },

  /* Butter */
  { id:'b1', user:{name:'Butter', avatar:'https://i.pravatar.cc/80?img=1'}, ts:'2小時前', text:'戶外散步集錦，一次放上四張～', type:'carousel', media:['images/200427-23094-01-Cuuu5.jpg','images/original.jpg','images/1382490545-442951735.jpg','images/southeast.jpg'], likes:12, comments:[] },
  { id:'b2', user:{name:'Butter', avatar:'https://i.pravatar.cc/80?img=1'}, ts:'昨天', text:'補水也很重要', type:'single', media:['images/ChatGPT Image05_34_03.PNG'], likes:7, comments:[] },
  { id:'b3', user:{name:'Butter', avatar:'https://i.pravatar.cc/80?img=1'}, ts:'3天前', text:'衝刺！', type:'video', media:['images/kling_20250829_Image_to_Video__4516_0.mp4'], likes:21, comments:[] },
  { id:'b4', user:{name:'Butter', avatar:'https://i.pravatar.cc/80?img=1'}, ts:'5天前', text:'曬太陽好舒服', type:'single', media:['images/ChatGPT Image05_54_42.PNG'], likes:5, comments:[] },

  /* Peanut */
  { id:'p1u', user:{name:'Peanut', avatar:'https://i.pravatar.cc/80?img=5'}, ts:'3小時前', text:'今天洗香香🛁', type:'carousel', media:['images/ChatGPT Image06_13_13.PNG','images/ChatGPT Image 06_18_40.PNG'], likes:8, comments:[] },
  { id:'p2u', user:{name:'Peanut', avatar:'https://i.pravatar.cc/80?img=5'}, ts:'昨天', text:'玩球時間', type:'video', media:['images/kling_20250829_Image_to_Video__4745_0.mp4'], likes:17, comments:[] },
  { id:'p3u', user:{name:'Peanut', avatar:'https://i.pravatar.cc/80?img=5'}, ts:'4天前', text:'午睡 zZz', type:'single', media:['images/ChatGPT Image03_03_33.PNG'], likes:3, comments:[] },
  { id:'p4u', user:{name:'Peanut', avatar:'https://i.pravatar.cc/80?img=5'}, ts:'6天前', text:'盯著零食罐…', type:'single', media:['images/ChatGPT Image 03_07_41.PNG'], likes:6, comments:[] },

  /* 小黑 */
  { id:'x1u', user:{name:'小黑', avatar:'https://i.pravatar.cc/80?img=8'}, ts:'1小時前', text:'巡邏地盤', type:'single', media:['images/ChatGPT Image03_33_46.PNG'], likes:6, comments:[] },
  { id:'x2u', user:{name:'小黑', avatar:'https://i.pravatar.cc/80?img=8'}, ts:'昨天', text:'玩飛盤！', type:'video', media:['影片專案.MP4'], likes:20, comments:[] },
  { id:'x3u', user:{name:'小黑', avatar:'https://i.pravatar.cc/80?img=8'}, ts:'5天前', text:'偷吃被抓包', type:'single', media:['images/ChatGPT Image 10_51_36.PNG'], likes:4, comments:[] },
  { id:'x4u', user:{name:'小黑', avatar:'https://i.pravatar.cc/80?img=8'}, ts:'6天前', text:'想出去玩🥺', type:'single', media:['images/ChatGPT Image 11_00_45.PNG'], likes:2, comments:[] },
  { id:'x5u', user:{name:'小黑', avatar:'https://i.pravatar.cc/80?img=8'}, ts:'3天前', text:'小黑今天去洗澡啦🛁', type:'carousel', media:['images/a5139e2a-54d9-427a-982a-a898c7d69034.png','images/6da1c8d2-5e89-4680-8e60-b1c8302ac816.png','images/d01badcf-644d-48de-837e-d6b9c7fe4ac8.png'], likes:5, comments:[] },
];

/****************************************************
 * 使用者主檔（維持/補齊）
 ****************************************************/
const userProfiles = {
  "Butter": { handle:"@butter", bio:"喜歡散步與曬太陽的奶油寶。", banner:"images/original.jpg", followers:1203, following:88 },
  "Peanut": { handle:"@peanut", bio:"Peanut小姐的日常集錦。",     banner:"images/ChatGPT Image 06_18_40.PNG", followers:842,  following:51 },
  "小黑":   { handle:"@小黑",   bio:"洗澡最帥的小黑 🛁",         banner:"images/a5139e2a-54d9-427a-982a-a898c7d69034.png", followers:564, following:33 },
  "逗逗":   { handle:"@逗逗",   bio:"我是啃骨頭小天才 🐶",       banner:"images/1080.webp", followers:1932, following:102 },
};
function getUserAvatar(name){
  const f = followData.find(x=>x.name===name);
  if (f) return f.avatar.replace('/24','/80');
  const p = postData.find(p=>p.user.name===name);
  return p ? p.user.avatar : 'https://i.pravatar.cc/80?u='+encodeURIComponent(name);
}

/****************************************************
 * 分享渠道設定（加上 null 防護，避免首頁空白）
 ****************************************************/
const shareChannels = [
  { id: 'line',   label: 'LINE' },
  { id: 'fb',     label: 'Facebook' },
  { id: 'x',      label: 'X (Twitter)' },
  { id: 'ig',     label: 'Instagram' },
  { id: 'email',  label: 'Email' },
  { id: 'copy',   label: '複製連結' },
  { id: 'system', label: '系統分享' },
];

const shareOverlay    = document.getElementById('shareOverlay');
const sharePreviewImg = document.getElementById('sharePreviewImg');
const shareChannelsEl = document.getElementById('shareChannels');
const shareCloseBtn   = document.getElementById('shareClose');
let sharePostId = null;

function openShareModal(post){
  if(!shareOverlay) return;
  sharePostId = post.id;
  if (sharePreviewImg) {
    // 影片就不放預覽，避免空白圖誤導
    const first = post.media?.[0] || '';
    sharePreviewImg.src = (post.type==='single'||post.type==='carousel') ? first : '';
  }
  shareOverlay.classList.add('active');
  shareOverlay.setAttribute('aria-hidden','false');
}
function closeShareModal(){
  if(!shareOverlay) return;
  sharePostId=null;
  shareOverlay.classList.remove('active');
  shareOverlay.setAttribute('aria-hidden','true');
}
if (shareCloseBtn) shareCloseBtn.addEventListener('click', closeShareModal);
if (shareOverlay)  shareOverlay.addEventListener('click', e=>{ if(e.target===shareOverlay) closeShareModal(); });

function renderShareChannels(){
  if (!shareChannelsEl) return;
  shareChannelsEl.innerHTML='';
  shareChannels.forEach(ch=>{
    const b=document.createElement('button');
    b.textContent=ch.label;
    b.dataset.channel = ch.id;
    b.addEventListener('click', onShareChannelClick);
    shareChannelsEl.appendChild(b);
  });
}

function getSharePayload(post){
  const url  = `${location.origin}${location.pathname}#${post.id}`;
  const text = `${post.user.name}: ${post.text}`.trim();
  const title = '毛孩社群平台';
  return { title, text, url };
}
function openWithFallback(appUrl, webUrl){
  setTimeout(()=>{ if (webUrl) window.open(webUrl, '_blank', 'noopener'); }, 1200);
  // 嘗試喚起 App
  window.location.href = appUrl;
}
async function shareViaWebAPI(payload){
  try{ if (navigator.share){ await navigator.share(payload); closeShareModal(); return true; } }
  catch(e){}
  return false;
}
function onShareChannelClick(e){
  const channel = e.currentTarget.dataset.channel;
  const post = findCurrentPostById(sharePostId);
  if (!post) return;

  const { title, text, url } = getSharePayload(post);
  if (channel === 'system'){ shareViaWebAPI({title,text,url}); return; }

  switch(channel){
    case 'line': { const msg=encodeURIComponent(`${text} ${url}`); openWithFallback(`line://msg/text/${msg}`, `https://line.me/R/msg/text/?${msg}`); break; }
    case 'fb':   window.open(`https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(url)}`,'_blank','noopener'); break;
    case 'x':    window.open(`https://twitter.com/intent/tweet?text=${encodeURIComponent(text)}&url=${encodeURIComponent(url)}`,'_blank','noopener'); break;
    case 'ig':   window.open('https://www.instagram.com/','_blank','noopener'); break;
    case 'email':{ const subject=encodeURIComponent(title); const body=encodeURIComponent(`${text}\n\n${url}`); window.location.href=`mailto:?subject=${subject}&body=${body}`; break; }
    case 'copy': {
      const toCopy = `${text} ${url}`.trim();
      if (navigator.clipboard?.writeText){
        navigator.clipboard.writeText(toCopy).then(()=>{ alert('已複製連結！'); closeShareModal(); }, ()=>fallbackCopy(toCopy));
      }else{ fallbackCopy(toCopy); }
      break;
    }
    default: shareViaWebAPI({title,text,url}) || alert('此分享目標不支援，請使用系統分享。');
  }
}
function fallbackCopy(text){
  const ta=document.createElement('textarea'); ta.value=text; ta.style.position='fixed'; ta.style.opacity='0';
  document.body.appendChild(ta); ta.select();
  try{ document.execCommand('copy'); alert('已複製連結！'); }catch{ alert('複製失敗'); }
  document.body.removeChild(ta);
  closeShareModal();
}

/****************************************************
 * 共用工具：當前是否在個人頁、目前資料源、以 ID 找貼文
 ****************************************************/
function currentRouteIsProfile(){
  return /^#\/user\/.+$/.test(decodeURIComponent(location.hash||''));
}
function currentUserName(){
  const m = decodeURIComponent(location.hash||'').match(/^#\/user\/(.+)$/);
  return m ? m[1] : null;
}
function currentPostsBase(){
  if (!currentRouteIsProfile()) return postData; // 首頁
  const u = currentUserName();
  return profilePosts.filter(p=>p.user.name===u);
}
function findCurrentPostById(id){
  if (!id) return null;
  const base = currentPostsBase();
  return base.find(p=>p.id===id) || null;
}

/****************************************************
 * 渲染：追蹤中清單（點擊導向個人頁）
 ****************************************************/
function renderFollowList(){
  const ul = document.getElementById('followList');
  if (!ul) return;
  ul.innerHTML = '';
  followData.forEach(f=>{
    const li = document.createElement('li');
    li.innerHTML = `<img src="${f.avatar}" alt="${f.name}"><span class="name">${f.name}</span>`;
    li.dataset.username = f.name;
    li.addEventListener('click', ()=>{ location.hash = '#/user/' + encodeURIComponent(f.name); });
    ul.appendChild(li);
  });
}

/****************************************************
 * 元件：留言、貼文卡、輪播
 ****************************************************/
function commentHtml(c,isReply){
  return `<div class="comment-item" data-commentid="${c.id}">
    <img src="${c.user.avatar}" alt="${c.user.name}">
    <div class="comment-bubble">
      <div class="comment-author">${c.user.name}</div>
      <div class="comment-text">${c.text}</div>
      <div class="comment-footer">
        <button class="comment-like" aria-label="like comment">👍 <span class="comment-like-count">${c.likes||0}</span></button>
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
    const srcPost = (currentRouteIsProfile() ? profilePosts : postData).find(x=>x.id===p.repostFrom);
    if(srcPost){ repostHtml = `<div class="repost-info">↻ 轉發自 ${srcPost.user.name}</div>`; }
  }

  let mediaHtml='';
  if(p.type==='single'){
    mediaHtml=`<div class="post-media-single"><img src="${p.media[0]}" alt="貼文圖片"></div>`;
  }else if(p.type==='carousel'){
    const imgs=p.media.map(url=>`<img src="${url}" alt="carousel-img">`).join('');
    const ind=p.media.map((_,i)=>`<button data-idx="${i}" aria-label="移動到第${i+1}張"></button>`).join('');
    mediaHtml=`<div class="carousel-wrapper" data-count="${p.media.length}">
      <div class="carousel-track">${imgs}</div>
      <button class="carousel-btn prev" aria-label="上一張">◀</button>
      <button class="carousel-btn next" aria-label="下一張">▶</button>
      <div class="carousel-indicators">${ind}</div>
    </div>`;
  }else if(p.type==='video'){
    mediaHtml=`<div class="post-media-single"><video controls preload="metadata" src="${p.media[0]}"></video></div>`;
  }

  const commentsHtml = (p.comments||[]).map(c=>{
    const repliesHtml = (c.replies||[]).map(r=>commentHtml(r,true)).join('');
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
      <button class="btn-like" aria-label="like"><span class="icon">🖤</span><span class="like-count">${p.likes||0}</span></button>
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
 * 首頁渲染、個人主頁渲染
 ****************************************************/
function renderFeed(){
  const feedEl = document.getElementById('feed');
  if (!feedEl) return;
  feedEl.innerHTML='';
  postData.forEach(p=>feedEl.appendChild(createPostCard(p)));
}

function renderUserProfile(name){
  const feedEl = document.getElementById('feed');
  if (!feedEl) return;
  feedEl.innerHTML='';

  // 頁首卡片
  const profile = userProfiles[name] || {handle:'@'+name, bio:'', banner:'', followers:0, following:0};
  const header = document.createElement('section');
  header.className='profile-card';
  header.innerHTML = `
    <div class="profile-banner" style="background-image:url('${profile.banner||''}')">
      <img class="profile-avatar" src="${getUserAvatar(name)}" alt="${name}">
    </div>
    <div class="profile-meta">
      <button class="profile-back" onclick="history.back()">← 返回</button>
      <div class="profile-name">${name}</div>
      <div class="profile-handle">${profile.handle}</div>
      <div class="profile-stats">
        <span><b>${(profile.followers||0).toLocaleString()}</b> 粉絲</span>
        <span><b>${(profile.following||0).toLocaleString()}</b> 追蹤中</span>
      </div>
      <p style="margin:8px 0 0;">${profile.bio||''}</p>
      <div class="profile-actions">
        <button class="btn">發訊息</button>
        <button class="btn">追蹤中</button>
      </div>
    </div>
  `;
  feedEl.appendChild(header);

  // 個人貼文
  const list = profilePosts.filter(p=>p.user.name===name);
  if (list.length===0){
    const empty=document.createElement('div');
    empty.className='post-card';
    empty.textContent='尚無貼文';
    feedEl.appendChild(empty);
  }else{
    list.forEach(p=>feedEl.appendChild(createPostCard(p)));
  }
}

/****************************************************
 * 互動事件：依目前路由操作正確的資料源
 ****************************************************/
document.addEventListener('click',function(e){
  const likeBtn = e.target.closest('.post-actions .btn-like');
  if(likeBtn){ togglePostLike(likeBtn); return; }

  const commentBtn = e.target.closest('.post-actions .btn-comment');
  if(commentBtn){
    const postCard = commentBtn.closest('.post-card');
    const input = postCard.querySelector('.add-comment input');
    if (input) input.focus();
    return;
  }

  const shareBtn = e.target.closest('.post-actions .btn-share');
  if(shareBtn){
    const postCard = shareBtn.closest('.post-card');
    const post = findCurrentPostById(postCard?.dataset.postid);
    if(post) openShareModal(post);
    return;
  }

  const repostBtn = e.target.closest('.post-actions .btn-repost');
  if(repostBtn){
    const postCard = repostBtn.closest('.post-card');
    const post = findCurrentPostById(postCard?.dataset.postid);
    if(post) repost(post);
    return;
  }

  const cLikeBtn = e.target.closest('.comment-footer .comment-like');
  if(cLikeBtn){ toggleCommentLike(cLikeBtn); return; }

  const replyBtn = e.target.closest('.comment-footer .comment-reply');
  if(replyBtn){ startReply(replyBtn); return; }

  const sendBtn = e.target.closest('.add-comment .send');
  if(sendBtn){
    const postCard = sendBtn.closest('.post-card');
    const inputEl = postCard.querySelector('.add-comment input');
    const replyTo = inputEl?.dataset.replyTo;
    addComment(postCard,inputEl,replyTo);
    if (inputEl){
      inputEl.value='';
      inputEl.placeholder='輸入留言…';
      delete inputEl.dataset.replyTo;
    }
    return;
  }
});

function togglePostLike(btn){
  const postCard = btn.closest('.post-card');
  const post = findCurrentPostById(postCard?.dataset.postid);
  if(!post) return;
  const countEl = btn.querySelector('.like-count');
  const iconEl = btn.querySelector('.icon');
  const hearted = btn.classList.toggle('hearted');
  post.likes = Math.max(0, (post.likes||0) + (hearted?1:-1));
  if(countEl) countEl.textContent = post.likes;
  if(iconEl)  iconEl.textContent = hearted ? '❤️' : '🖤';
}

function toggleCommentLike(btn){
  const commentItem = btn.closest('.comment-item');
  const postCard = btn.closest('.post-card');
  const post = findCurrentPostById(postCard?.dataset.postid);
  if(!post) return;
  const cid = commentItem?.dataset.commentid;
  let comment = null;
  for(const c of (post.comments||[])){
    if(c.id===cid){comment=c;break;}
    const r = (c.replies||[]).find(x=>x.id===cid);
    if(r){comment=r;break;}
  }
  if(!comment) return;
  const countEl = btn.querySelector('.comment-like-count');
  const liked = btn.classList.toggle('liked');
  comment.likes = Math.max(0, (comment.likes||0) + (liked?1:-1));
  if(countEl) countEl.textContent = comment.likes;
}

function addComment(postCard,inputEl,isReplyTo){
  if(!postCard || !inputEl) return;
  const txt = (inputEl.value||'').trim();
  if(!txt) return;
  const post = findCurrentPostById(postCard.dataset.postid);
  if(!post) return;
  const newC = {id:'c'+Date.now(),user:{name:'我',avatar:'https://i.pravatar.cc/40?u=me'},text:txt,likes:0,replies:[]};
  if(isReplyTo){
    const target = (post.comments||[]).find(c=>c.id===isReplyTo);
    if(target) (target.replies||(target.replies=[])).push(newC);
  }else{
    (post.comments||(post.comments=[])).push(newC);
  }
  // 重新渲染當前頁
  route();
}

function startReply(btn){
  const commentItem = btn.closest('.comment-item');
  const postCard = btn.closest('.post-card');
  const cid = commentItem?.dataset.commentid;
  const inputEl = postCard?.querySelector('.add-comment input');
  if(!cid || !inputEl) return;
  inputEl.placeholder = '回覆…';
  inputEl.focus();
  inputEl.dataset.replyTo = cid;
}

function repost(post){
  const newPost = {
    id:'rp'+Date.now(),
    user:{name:'我', avatar:'https://i.pravatar.cc/80?u=me'},
    ts:'剛剛',
    text:post.text, type:post.type, media:(post.media||[]).slice(),
    likes:0, comments:[], repostFrom:post.id,
  };
  if (currentRouteIsProfile()){
    profilePosts.unshift(newPost); // 個人頁只影響個人頁資料
  }else{
    postData.unshift(newPost);     // 首頁只影響首頁資料
  }
  route();
  window.scrollTo({top:0,behavior:'smooth'});
}

/****************************************************
 * 搜尋：首頁搜首頁資料，個人頁只搜該使用者資料
 ****************************************************/
const searchInput = document.getElementById('searchInput');
if (searchInput){
  searchInput.addEventListener('input', e => {
    const keyword = (e.target.value||'').trim().toLowerCase();
    const feedEl = document.getElementById('feed');
    if (!feedEl) return;

    if (!keyword){
      route(); // 清空→回到當前頁的完整列表
      return;
    }

    const base = currentPostsBase();
    const filtered = base.filter(p=>{
      const textMatch = (p.text||'').toLowerCase().includes(keyword);
      const userMatch = (p.user?.name||'').toLowerCase().includes(keyword);
      const tagMatch  = (p.text||'').toLowerCase().includes('#'+keyword);
      return textMatch || userMatch || tagMatch;
    });

    // 若在個人頁，需要保留個人頁頭像卡
    if (currentRouteIsProfile()){
      const u = currentUserName();
      renderUserProfile(u);
      const container = document.getElementById('feed');
      // 移除 header 以外的卡片後再插入過濾結果
      const header = container.firstChild; // profile-card
      while (container.childNodes.length > 1) container.removeChild(container.lastChild);
      filtered.forEach(p=>container.appendChild(createPostCard(p)));
    }else{
      feedEl.innerHTML='';
      filtered.forEach(p=>feedEl.appendChild(createPostCard(p)));
    }
  });
}

/****************************************************
 * 路由：#/user/名字 → 個人主頁；其他 → 首頁
 ****************************************************/
function route(){
  const u = currentUserName();
  if (u){ renderUserProfile(u); }
  else { renderFeed(); }
}

/****************************************************
 * 啟動
 ****************************************************/
renderFollowList();
renderShareChannels();
window.addEventListener('hashchange', route);
route(); // 初次載入就依 hash 決定顯示
