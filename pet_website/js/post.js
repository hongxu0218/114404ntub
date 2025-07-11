const currentUser = "你";

function getTimeString() {
  return new Date().toLocaleString('zh-TW');
}

function toggleLike(el) {
  const heart = el.querySelector('.like-icon');
  const count = el.querySelector('span');
  const liked = heart.textContent === '❤️';
  heart.textContent = liked ? '🖤' : '❤️';
  count.innerText = liked ? parseInt(count.innerText) - 1 : parseInt(count.innerText) + 1;
}

function toggleComment(postId) {
  const section = document.querySelector(`#${postId} .comment-section`);
  section.style.display = section.style.display === 'none' ? 'block' : 'none';
}

function likeComment(el) {
  const span = el.querySelector('span');
  span.innerText = parseInt(span.innerText) + 1;
}

function addComment(postId, parent = null) {
  const input = parent ? parent.querySelector('input') : document.querySelector(`#${postId} .new-comment input`);
  const text = input.value.trim();
  if (!text) return;

  const comment = document.createElement('div');
  comment.className = parent ? 'reply' : 'comment';
  comment.innerHTML = `
    <div><strong>${currentUser}</strong>：${text} <span class="timestamp">${getTimeString()}</span></div>
    <div>
      <span class="comment-like" onclick="likeComment(this)">👍 <span>0</span></span>
      <button onclick="toggleReply(this)">回覆</button>
    </div>
    <div class="new-comment" style="display:none;">
      <input type="text" placeholder="輸入回覆...">
      <button onclick="addComment('${postId}', this.parentElement.parentElement)">送出</button>
    </div>
  `;
  const section = parent || document.querySelector(`#${postId} .comment-section`);
  section.insertBefore(comment, section.querySelector('.new-comment'));
  input.value = '';
}

function toggleReply(el) {
  const box = el.parentElement.nextElementSibling;
  box.style.display = box.style.display === 'none' ? 'flex' : 'none';
}

function copyLink() {
  navigator.clipboard.writeText("https://youtu.be/abc123");
  alert("已複製分享連結！");
}

function closeModal() {
  document.getElementById('shareModal').style.display = 'none';
}

function openModal() {
  document.getElementById('shareModal').style.display = 'flex';
}

function repost(postId) {
  const original = document.getElementById(postId);
  const clone = original.cloneNode(true);
  const newId = postId + '_repost_' + Date.now();
  clone.id = newId;
  const header = clone.querySelector('h2');
  header.innerText = `${currentUser} 轉發了 ${header.innerText}`;
  document.getElementById('mainContent').prepend(clone);
}

const posts = [
  {
    id: 'post1',
    user: 'Hailey',
    avatar: 'https://randomuser.me/api/portraits/women/44.jpg',
    text: '逗逗啃寵物骨頭好可愛！',
    image: 'images/1080.webp',
    likes: 20
  },
  {
    id: 'post2',
    user: 'yyselina',
    avatar: 'https://randomuser.me/api/portraits/women/12.jpg',
    text: '今天帶狗狗去洗澡，好香好乾淨！',
    image: 'images/shower.jpg',
    likes: 5
  },
  {
    id: 'post3',
    user: 'Butter',
    avatar: 'https://randomuser.me/api/portraits/women/8.jpg',
    text: '今天帶狗狗去散步遇到好多狗狗，真可愛!',
    image: 'images/1024x706.jpeg',
    likes: 10
  }
];

const main = document.getElementById('mainContent');
posts.forEach(post => {
  const div = document.createElement('div');
  div.className = 'post';
  div.id = post.id;
  div.innerHTML = `
    <div class="post-header">
      <img src="${post.avatar}" alt="avatar" class="avatar">
      <div>
        <h2>${post.user}</h2>
        <div class="timestamp">由 ${post.user} 發布 · ${getTimeString()}</div>
      </div>
    </div>
    <p>${post.text}</p>
    <img src="${post.image}" alt="貼文圖片" class="media">
    <div class="actions">
      <span onclick="toggleLike(this)"><span class="like-icon">🖤</span> <span>${post.likes}</span></span>
      <button onclick="toggleComment('${post.id}')">💬 留言</button>
      <button onclick="openModal()">🔗 分享</button>
      <button onclick="repost('${post.id}')">🔁 轉發</button>
    </div>
    <div class="comment-section" style="display:none;">
      <div class="comment">
        <div><strong>訪客A</strong>：太萌了！ <span class="timestamp">${getTimeString()}</span></div>
        <div>
          <span class="comment-like" onclick="likeComment(this)">👍 <span>2</span></span>
          <button onclick="toggleReply(this)">回覆</button>
        </div>
        <div class="new-comment" style="display:none;">
          <input type="text" placeholder="輸入回覆...">
          <button onclick="addComment('${post.id}', this.parentElement.parentElement)">送出</button>
        </div>
      </div>
      <div class="new-comment">
        <input type="text" placeholder="輸入留言...">
        <button onclick="addComment('${post.id}')">送出</button>
      </div>
    </div>
  `;
  main.appendChild(div);
});
