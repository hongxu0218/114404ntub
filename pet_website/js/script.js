
function initMap() {
  const map = new google.maps.Map(document.getElementById("map"), {
    center: { lat: 25.033964, lng: 121.564468 },
    zoom: 14,
  });
}
document.querySelectorAll('.tag').forEach(tag => {
  tag.addEventListener('click', () => {
    document.getElementById('results').innerHTML = `
      <div class="result-item">🔍 搜尋：${tag.innerText} 結果 A</div>
      <div class="result-item">${tag.innerText} 結果 B</div>
      <div class="result-item">${tag.innerText} 結果 C</div>
    `;
  });
});
document.getElementById('searchBtn').addEventListener('click', () => {
  const keyword = document.getElementById('searchInput').value;
  document.getElementById('results').innerHTML = `
    <div class="result-item">🔍 ${keyword} 搜尋結果 A</div>
    <div class="result-item">${keyword} 結果 B</div>
    <div class="result-item">${keyword} 結果 C</div>
  `;
});

