/**
 * PAW&DAY 領養專區
 * 新增送養寵物頁面
 */
document.addEventListener("DOMContentLoaded", function () {
    // ===== DOM 元素 =====
    const petSelect = document.getElementById('my_pet_select'); // 從我的寵物下拉
    const fileInput = document.getElementById("id_adopt_picture1");
    const previewImg  = document.getElementById("preview1");
    const usePetImageInput = document.getElementById("use_pet_image");

    let myPets = [];
    const myPetsEl = document.getElementById("myPetsData");
    if (myPetsEl) {
        try {
            myPets = JSON.parse(myPetsEl.textContent);
        } catch(e) {
            console.error("解析 myPetsData 失敗", e);
        }
    } else {
        console.error("myPetsData element not found");
    }

    const fakeInput = document.getElementById("id_adopt_picture1_fake");
    const fileWrapper = document.querySelector('.file-wrapper');

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

    const featureChoiceSelect = document.getElementById('id_feature_choice');
    const featureOtherInput = document.getElementById('id_feature_other');
    const featureOtherGroup = document.getElementById('feature-other-group');

    const form = document.getElementById("add-adoption-form");
    const nameInput = document.getElementById("id_name");


    // ===== 後端傳入 JSON =====
    const dogBreeds = JSON.parse(document.getElementById('dogBreedsData').textContent || '[]');
    const catBreeds = JSON.parse(document.getElementById('catBreedsData').textContent || '[]');
    const dogVaccines = JSON.parse(document.getElementById('dogVaccinesData').textContent || '[]');
    const catVaccines = JSON.parse(document.getElementById('catVaccinesData').textContent || '[]');
    const otherPetNames = JSON.parse(document.getElementById('otherPetNamesData').textContent || '[]');
    const featureChoices = JSON.parse(document.getElementById('featureChoicesData').textContent || "[]");

    // 更新 fake input 和 title
    function updateFakeInput(filename) {
        if (!filename) filename = "沒有選擇檔案";
        fakeInput.value = filename;
        fileWrapper.title = filename;
    }




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






// ===== 選擇「我的寵物」 =====
// 通用函式：填入基本欄位
function fillPetForm(selectedPet) {
    const fieldMap = {
        'name': 'id_name',
        "species":"id_species",
        "breed":"id_breed",
        "feature":"id_feature",
        'gender': 'id_gender',
        'birth_date': 'id_birth_date',
        'chip': 'id_chip',
        'weight': 'id_weight',
        'sterilization_status': 'id_sterilization_status',
        'picture': 'preview1'  // 假設第一張圖片預覽用 preview1
    };

    Object.entries(fieldMap).forEach(([key, elId]) => {
        const el = document.getElementById(elId);
        if (!el || selectedPet[key] === undefined) return;
        if (el.tagName === 'INPUT' || el.tagName === 'SELECT' || el.tagName === 'TEXTAREA') {
            el.value = selectedPet[key];
            }
        else if (
            el.tagName === 'IMG' && key === 'picture') {
            el.src = selectedPet[key]; el.style.display = 'block';
        }
    });


    // ---- 種類 ----
    const speciesVal = ['狗','貓','其他'].includes(selectedPet.species)
                        ? selectedPet.species
                        : '其他';
    speciesSelect.value = speciesVal;
    hiddenSpecies.value = speciesVal;

    if (speciesVal === '其他') {
        speciesOtherInput.value = selectedPet.species;
        speciesOtherGroup.style.display = 'block';
    } else {
        speciesOtherInput.value = '';
        speciesOtherGroup.style.display = 'none';
    }

    // 更新品種 & 疫苗選項
    updateSpecies(); // 你原本 JS 的函式

    // ---- 品種 ----
    let breedData = {breed_choice: selectedPet.breed, breed_other: ''};
    try {
        if (typeof selectedPet.breed === 'string' && selectedPet.breed.startsWith('{')) {
            breedData = JSON.parse(selectedPet.breed);
        }
    } catch(e){ console.error("解析 breed JSON 失敗", e); }

    if (breedData.breed_choice === '其他' || ![...dogBreeds.map(b=>b[0]), ...catBreeds.map(b=>b[0])].includes(breedData.breed_choice)) {
        breedSelect.value = '其他';
        breedOtherInput.value = breedData.breed_other || breedData.breed_choice;
        breedOtherGroup.style.display = 'block';
    } else {
        breedSelect.value = breedData.breed_choice;
        breedOtherInput.value = '';
        breedOtherGroup.style.display = 'none';
    }
    hiddenBreed.value = breedSelect.value;

    // ---- 個性特徵 ----
    const featVal = featureChoices.includes(selectedPet.feature) ? selectedPet.feature : '其他';
    featureChoiceSelect.value = featVal;
    if (featVal === '其他') {
        featureOtherInput.value = selectedPet.feature;
        featureOtherGroup.style.display = 'block';
    } else {
        featureOtherInput.value = '';
        featureOtherGroup.style.display = 'none';
    }

    // ---- 疫苗帶入 ----
    if (selectedPet.vaccine_records && selectedPet.vaccine_records.length > 0) {
        // 去重
        const uniqueVaccines = Array.from(new Set(selectedPet.vaccine_records));

        // 合併成逗號字串
        const vaccineStr = uniqueVaccines.join('，');

        // 預設先清空
        vaccineSelect.value = '';
        vaccineOtherInput.value = '';
        vaccineOtherGroup.style.display = 'none';

        // 檢查字串是否在下拉選單
        let allOptions = Array.from(vaccineSelect.options).map(o => o.value);
        if (uniqueVaccines.every(v => allOptions.includes(v))) {
            // 全部選項都存在，就選第一個
            vaccineSelect.value = uniqueVaccines[0];
            if (uniqueVaccines.length > 1) {
                // 多個就放到其他輸入框
                vaccineSelect.value = '其他';
                vaccineOtherInput.value = vaccineStr;
                vaccineOtherGroup.style.display = 'block';
            }
        } else {
            // 有不在選項裡的就放「其他疫苗」
            vaccineSelect.value = '其他';
            vaccineOtherInput.value = vaccineStr;
            vaccineOtherGroup.style.display = 'block';
        }
    } else {
        vaccineSelect.value = '';
        vaccineOtherInput.value = '';
        vaccineOtherGroup.style.display = 'none';
    }

}

/**
 * 更新圖片預覽
 * @param {HTMLInputElement} fileInput - 真實的檔案輸入
 * @param {HTMLImageElement} previewImg - 預覽圖片
 * @param {HTMLInputElement} usePetImageInput - hidden 欄位，標記來源 (0=使用者上傳, 1=寵物帶入)
 * @param {Object} pet - 選擇的寵物 (可選)
 * @param {Boolean} forcePet - 是否強制帶入寵物圖片 (例如切換寵物時)
 */
function updatePicturePreview(fileInput, previewImg, usePetImageInput, pet = null, forcePet = false) {
    if (!fileInput || !previewImg || !usePetImageInput) return;

    // 1️⃣ 優先：使用者上傳檔案 (除非強制帶入寵物圖片)
    if (!forcePet && fileInput.files && fileInput.files.length > 0) {
        const reader = new FileReader();
        reader.onload = function(e) {
            previewImg.src = e.target.result;
            previewImg.style.display = "block";
        };
        reader.readAsDataURL(fileInput.files[0]);

        usePetImageInput.value = "0"; // 來源 = 使用者上傳
        updateFakeInput(fileInput.files[0].name);
        return;
    }

    // 2️⃣ 帶入寵物圖片
    if (pet && pet.picture) {
        previewImg.src = pet.picture;
        previewImg.style.display = "block";

        usePetImageInput.value = "1"; // 來源 = 寵物帶入
        updateFakeInput(pet.picture_filename || "已帶入圖片");

        // ⚠️ 清掉使用者上傳的檔案
        fileInput.value = "";
        return;
    }

    // 3️⃣ 沒有任何圖片
    previewImg.src = "";
    previewImg.style.display = "none";
    usePetImageInput.value = "0";
    updateFakeInput(null);
    fileInput.value = "";
}
fileInput.addEventListener("change", () => {
    updatePicturePreview(fileInput, previewImg, usePetImageInput);
    if (fileInput.files.length > 0) {
            fakeInput.value = fileInput.files[0].name;
        } else {
            fakeInput.value = "沒有選擇檔案";
        }
});
petSelect.addEventListener("change", function() {
    const selectedPet = myPets.find(p => p.id == this.value);
    if (!selectedPet) return;

    // 強制帶入寵物圖片
    updatePicturePreview(fileInput, previewImg, usePetImageInput, selectedPet, true);

    // 也可以同時呼叫 fillPetForm
    fillPetForm(selectedPet);
});


fakeInput.addEventListener("click", () => {
    fileInput.click();
});

            // 預設顯示「沒有選擇檔案」
            updateFakeInput(null);


});


