(() => {
  const year = document.getElementById("year");
  if (year) {
    year.textContent = String(new Date().getFullYear());
  }

  const tabs = Array.from(document.querySelectorAll("[data-tab-target]"));
  const panels = Array.from(document.querySelectorAll(".upload-panel"));
  const dropzones = Array.from(document.querySelectorAll("[data-dropzone]"));

  function showPanel(panelId) {
    panels.forEach((panel) => {
      const isActive = panel.id === panelId;
      panel.hidden = !isActive;
      panel.classList.toggle("is-active", isActive);
    });

    tabs.forEach((tab) => {
      const isActive = tab.dataset.tabTarget === panelId;
      tab.classList.toggle("is-active", isActive);
      tab.setAttribute("aria-selected", String(isActive));
    });
  }

  tabs.forEach((tab) => {
    tab.addEventListener("click", () => showPanel(tab.dataset.tabTarget));
  });

  function updateFileLabel(dropzone, file) {
    const fileLabel = dropzone.querySelector("[data-file-name]");
    if (fileLabel) {
      fileLabel.textContent = file ? file.name : "No file selected";
    }
  }

  dropzones.forEach((dropzone) => {
    const input = dropzone.querySelector('input[type="file"]');

    if (!input) {
      return;
    }

    input.addEventListener("change", () => {
      updateFileLabel(dropzone, input.files[0]);
    });

    dropzone.addEventListener("dragover", (event) => {
      event.preventDefault();
      dropzone.classList.add("is-dragover");
    });

    dropzone.addEventListener("dragleave", () => {
      dropzone.classList.remove("is-dragover");
    });

    dropzone.addEventListener("drop", (event) => {
      event.preventDefault();
      dropzone.classList.remove("is-dragover");

      const file = event.dataTransfer.files[0];
      if (!file) {
        return;
      }

      const transfer = new DataTransfer();
      transfer.items.add(file);
      input.files = transfer.files;
      updateFileLabel(dropzone, file);
    });
  });

  if (tabs.length > 0 && panels.length > 0) {
    showPanel(tabs[0].dataset.tabTarget);
  }
})();
