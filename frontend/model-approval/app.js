"use strict";

const typeField = document.querySelector("#task-type");
const providerChoice = document.querySelector("#provider-choice");
const modelChoice = document.querySelector("#model-choice");
const customProviderRow = document.querySelector("#custom-provider-row");
const customProvider = document.querySelector("#custom-provider");
const modelField = document.querySelector("#model-id");
const scopeField = document.querySelector("#scope");
const confirmField = document.querySelector("#confirm");
const submitButton = document.querySelector("#submit");
const result = document.querySelector("#result");

let models = [];

function providerValue() {
  return providerChoice.value === "__custom__"
    ? customProvider.value.trim()
    : providerChoice.value;
}

function updateButton() {
  submitButton.disabled = !(
    confirmField.checked &&
    providerValue() &&
    modelField.value.trim() &&
    scopeField.value.trim()
  );
}

function clearModel() {
  modelField.value = "";
  modelField.readOnly = true;
  updateButton();
}

function populateModels() {
  const provider = providerValue();
  const matching = models.filter((model) =>
    model.provider === provider &&
    (typeField.value === "other" || model.task_types.includes(typeField.value))
  );

  modelChoice.replaceChildren(new Option("Выберите модель…", ""));
  matching.forEach((model, index) => {
    const option = new Option(model.label, String(index));
    option.title = model.note || "";
    modelChoice.add(option);
  });
  modelChoice.add(new Option("Ввести ID модели вручную…", "__custom__"));
  modelChoice.disabled = !provider;
  clearModel();
}

async function loadRegistry() {
  const response = await fetch("/api/models");
  if (!response.ok) {
    throw new Error("Не удалось прочитать локальный список моделей");
  }

  const registry = await response.json();
  models = registry.models;
  providerChoice.replaceChildren(new Option("Выберите провайдера…", ""));
  for (const provider of registry.providers || []) {
    providerChoice.add(new Option(provider.label, provider.id));
  }
  providerChoice.add(new Option("Другой провайдер…", "__custom__"));
  modelChoice.replaceChildren(new Option("Сначала выберите провайдера…", ""));
}

providerChoice.addEventListener("change", () => {
  confirmField.checked = false;
  const isCustom = providerChoice.value === "__custom__";
  customProviderRow.hidden = !isCustom;
  customProvider.required = isCustom;
  if (!isCustom) {
    customProvider.value = "";
  }
  populateModels();
});

typeField.addEventListener("change", () => {
  confirmField.checked = false;
  populateModels();
});

modelChoice.addEventListener("change", () => {
  confirmField.checked = false;
  if (modelChoice.value === "__custom__") {
    modelField.readOnly = false;
    modelField.value = "";
    modelField.focus();
  } else if (modelChoice.value === "") {
    clearModel();
  } else {
    const matching = models.filter((model) =>
      model.provider === providerValue() &&
      (typeField.value === "other" || model.task_types.includes(typeField.value))
    );
    modelField.readOnly = true;
    modelField.value = matching[Number(modelChoice.value)]?.model_id || "";
  }
  updateButton();
});

customProvider.addEventListener("input", () => {
  confirmField.checked = false;
  populateModels();
});

for (const field of [modelField, scopeField]) {
  field.addEventListener("input", () => {
    confirmField.checked = false;
    updateButton();
  });
  field.addEventListener("change", () => {
    confirmField.checked = false;
    updateButton();
  });
}

confirmField.addEventListener("change", updateButton);

document.querySelector("#approval-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  submitButton.disabled = true;
  result.textContent = "Сохраняю локальное одноразовое разрешение…";
  try {
    const response = await fetch("/api/approve", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        provider: providerValue(),
        model_id: modelField.value,
        task_scope: scopeField.value
      })
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || "Не удалось создать разрешение");
    }
    result.textContent = `Разрешение создано. ID: ${data.id} · истекает: ${
      new Date(data.expires_at).toLocaleString()
    }`;
    confirmField.checked = false;
  } catch (error) {
    result.textContent = error.message;
  }
  updateButton();
});

loadRegistry().catch((error) => {
  result.textContent = error.message;
});
