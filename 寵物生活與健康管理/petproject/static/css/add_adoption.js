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
    } else {
      groupEl.style.display = 'none';
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

});