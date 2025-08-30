/**
 * PAW&DAY 領養專區
 * 新增送養寵物頁面
 */
document.addEventListener("DOMContentLoaded", function () {
    // ===== DOM 元素 =====
    const speciesSelect = document.getElementById('species_select');
    const speciesOtherGroup = document.getElementById('species_other_group');
    const speciesOtherInput = document.getElementById('id_species_other');
    const hiddenSpecies = document.getElementById('id_species');

    const breedSelect = document.getElementById('breed_select');
    const breedOtherGroup = document.getElementById('breed_other_group');
    const breedOtherInput = document.getElementById('id_breed_other');
    const hiddenBreed = document.getElementById('id_breed');

    const vaccineSelect = document.getElementById('vaccine_select');
    const vaccineOtherGroup = document.getElementById('vaccine_other_group');
    const vaccineOtherInput = document.getElementById('id_vaccine_other');
    const hiddenVaccine = document.getElementById('id_vaccine');

    const form = document.getElementById("add-adoption-form");
    const nameInput = document.getElementById("id_name");

    // ===== 後端傳入 JSON =====
    const dogBreeds = JSON.parse(document.getElementById('dogBreedsData').textContent || '[]');
    const catBreeds = JSON.parse(document.getElementById('catBreedsData').textContent || '[]');
    const dogVaccines = JSON.parse(document.getElementById('dogVaccinesData').textContent || '[]');
    const catVaccines = JSON.parse(document.getElementById('catVaccinesData').textContent || '[]');
    const otherPetNames = JSON.parse(document.getElementById('otherPetNamesData').textContent || '[]');

    // ===== 函式: 更新品種 =====
    function updateBreed() {
        hiddenBreed.value = breedSelect.value;
        if (breedSelect.value === '其他') {
            breedOtherGroup.style.display = 'block';
            breedOtherInput.setAttribute("required", "required");
        } else {
            breedOtherGroup.style.display = 'none';
            breedOtherInput.removeAttribute("required");
            breedOtherInput.value = '';
        }
    }

    // ===== 函式: 更新疫苗 =====
    function updateVaccine() {
        hiddenVaccine.value = vaccineSelect.value;
        if (vaccineSelect.value === '其他') {
            vaccineOtherGroup.style.display = 'block';
            vaccineOtherInput.setAttribute("required", "required");
        } else {
            vaccineOtherGroup.style.display = 'none';
            vaccineOtherInput.removeAttribute("required");
            vaccineOtherInput.value = '';
        }
    }

    // ===== 函式: 更新種類 =====
function updateSpecies() {
    hiddenSpecies.value = speciesSelect.value;

    // 更新品種選項
    let breeds = [['', '請選擇']];
    if (speciesSelect.value === '狗') breeds = breeds.concat(dogBreeds);
    if (speciesSelect.value === '貓') breeds = breeds.concat(catBreeds);
    if (speciesSelect.value === '其他') breeds.push(['其他', '其他']);
    breedSelect.innerHTML = breeds.map(o => `<option value="${o[0]}">${o[1]}</option>`).join('');

    // 更新疫苗選項
    let vaccines = [['', '請選擇']];
    if (speciesSelect.value === '狗') vaccines = vaccines.concat(dogVaccines);
    if (speciesSelect.value === '貓') vaccines = vaccines.concat(catVaccines);
    if (speciesSelect.value === '其他') vaccines.push(['其他', '其他']);
    vaccineSelect.innerHTML = vaccines.map(o => `<option value="${o[0]}">${o[1]}</option>`).join('');

    if (speciesSelect.value === '其他') {
        speciesOtherGroup.style.display = 'block';
        speciesOtherInput.setAttribute("required", "required");
        // 自動選擇品種/疫苗其他
        breedSelect.value = '其他';
        vaccineSelect.value = '其他';
    } else {
        speciesOtherGroup.style.display = 'none';
        speciesOtherInput.removeAttribute("required");
        speciesOtherInput.value = '';
    }

    // 呼叫更新函式確保「其他」文字框顯示
    updateBreed();
    updateVaccine();
}


    // ===== 事件綁定 =====
    speciesSelect.addEventListener('change', updateSpecies);
    breedSelect.addEventListener('change', updateBreed);
    vaccineSelect.addEventListener('change', updateVaccine);

    // ===== 提交前同步 hidden =====
    if (form) {
        form.addEventListener('submit', function (e) {
            if (speciesSelect.value === '其他') hiddenSpecies.value = speciesOtherInput.value.trim();
            if (breedSelect.value === '其他') hiddenBreed.value = breedOtherInput.value.trim();
            if (vaccineSelect.value === '其他') hiddenVaccine.value = vaccineOtherInput.value.trim();

            // 名字重複檢查
            const enteredName = nameInput.value.trim().toLowerCase();
            if (otherPetNames.includes(enteredName)) {
                const confirmAdd = confirm("已有這個名字的毛孩，還是確定新增嗎？");
                if (!confirmAdd) e.preventDefault();
            }
          });
    }

    // ===== 圖片預覽 =====
  // 圖片預覽，支援多張圖片預覽
  const previewMap = {
    'id_adopt_picture1': 'preview1',
    'id_adopt_picture2': 'preview2',
    'id_adopt_picture3': 'preview3',
    'id_adopt_picture4': 'preview4'
  };

  Object.entries(previewMap).forEach(([inputId, previewId]) => {
    const input = document.getElementById(inputId);
    const preview = document.getElementById(previewId);

    if (input && preview) {
      input.addEventListener('change', function () {
        if (input.files && input.files[0]) {
          const reader = new FileReader();
          reader.onload = function (e) {
            preview.src = e.target.result;
            preview.style.display = 'block';
          };
          reader.readAsDataURL(input.files[0]);
        }
      });
    }
  });

    // ===== 初始化 =====
    updateSpecies();



// --- 個性特徵/健康狀況/領養條件 的顯示切換 ---
function setupOtherToggle(selectId, groupId, inputId) {
  const selectEl = document.getElementById(selectId);
  const groupEl = document.getElementById(groupId);
  const inputEl = document.getElementById(inputId);

  function toggle() {
    if (selectEl.value === '其他') {
      groupEl.style.display = 'block';
      inputEl.setAttribute("required", "required");
    } else {
      groupEl.style.display = 'none';
      inputEl.removeAttribute("required");
      inputEl.value = '';
    }
  }

  selectEl.addEventListener('change', toggle);
  toggle(); // 初次載入檢查
}

// 使用範例
setupOtherToggle('id_feature_choice', 'feature-other-group', 'id_feature_other');
setupOtherToggle('id_physical_condition_choice', 'physical-condition-other-group', 'id_physical_condition_other');
setupOtherToggle('id_adoption_condition_choice', 'adoption-condition-other-group', 'id_adoption_condition_other');





//////////////////////////
//////Textarea 的 展開/收合
////////////////////////
    const textareas = document.querySelectorAll(".auto-grow-textarea");
    const maxRows = 5;     // 最多顯示 5 行

  // 取得實際 line-height（避免手動估錯）
  function getLineHeightPx(el) {
    const lh = parseFloat(getComputedStyle(el).lineHeight);
    if (!isNaN(lh)) return lh + 2;
    const fs = parseFloat(getComputedStyle(el).fontSize) || 16;
    return 1.5 * fs + 2; // 後備：line-height: 1.5
  }

  // 移除每行末尾多餘空白 + 移除尾端空白行
  function trimTrailingBlankLines(str) {
    return str
      .replace(/[ \t]+\n/g, "\n") // 行尾空白
      .replace(/\n+$/g, "")       // 多餘結尾空行
      .replace(/\s+$/g, "");      // 任何尾端空白
  }

  // 編輯中：無上限展開
  function expandFully(el) {
    el.style.height = "auto";
    el.style.overflowY = "hidden";
    el.style.height = el.scrollHeight + "px";
  }

  // 閒置（blur/初始）：刪尾端空行後，<=5行顯示全部，>5行限制5行
  function clampWhenIdle(el) {
    const lineHeight = getLineHeightPx(el);
    const maxHeight = lineHeight * maxRows;

    const trimmed = trimTrailingBlankLines(el.value);
    if (trimmed !== el.value) el.value = trimmed;

    el.style.height = "auto";
    requestAnimationFrame(() => {
      const h = Math.min(el.scrollHeight, maxHeight);
      el.style.height = h + "px";
    });
  }

  textareas.forEach((ta) => {
    // 初始載入：先收斂
    clampWhenIdle(ta);

    // 點擊/聚焦：馬上完全展開
    ta.addEventListener("focus", () => expandFully(ta));

    // 輸入時：即時無上限展開
    ta.addEventListener("input", () => expandFully(ta));

    // 離開時：刪尾端空行並收斂
    ta.addEventListener("blur", () => clampWhenIdle(ta));
  });

  // 可選：字體/版面晚載入時再校正一次
  window.addEventListener("load", () => textareas.forEach(clampWhenIdle));







});