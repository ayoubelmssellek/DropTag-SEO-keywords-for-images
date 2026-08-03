(() => {
  const form = document.getElementById("tag-form");
  const dropzone = document.getElementById("dropzone");
  const fileInput = document.getElementById("file-input");
  const fileList = document.getElementById("file-list");
  const submitBtn = document.getElementById("submit-btn");
  const toast = document.getElementById("toast");
  const ratingInput = document.getElementById("rating");
  const starBtns = [...document.querySelectorAll("#stars button")];

  /** @type {{ file: File, url: string }[]} */
  let items = [];

  function showToast(message, isError = false) {
    toast.hidden = false;
    toast.textContent = message;
    toast.classList.toggle("is-error", isError);
  }

  function hideToast() {
    toast.hidden = true;
  }

  function setRating(value) {
    const n = Math.max(1, Math.min(5, Number(value) || 5));
    ratingInput.value = String(n);
    starBtns.forEach((btn) => {
      const v = Number(btn.dataset.value);
      btn.classList.toggle("on", v <= n);
    });
  }

  starBtns.forEach((btn) => {
    btn.addEventListener("click", () => setRating(btn.dataset.value));
    btn.addEventListener("mouseenter", () => {
      const hover = Number(btn.dataset.value);
      starBtns.forEach((b) => {
        b.classList.toggle("is-hover", Number(b.dataset.value) <= hover);
      });
    });
    btn.addEventListener("mouseleave", () => {
      starBtns.forEach((b) => b.classList.remove("is-hover"));
    });
  });
  setRating(5);

  function formatSize(bytes) {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }

  function clearItems() {
    items.forEach((item) => URL.revokeObjectURL(item.url));
    items = [];
  }

  function renderFiles() {
    fileList.innerHTML = "";
    if (!items.length) {
      fileList.hidden = true;
      dropzone.classList.remove("has-files");
      return;
    }
    fileList.hidden = false;
    dropzone.classList.add("has-files");
    items.forEach((item, index) => {
      const li = document.createElement("li");
      const img = document.createElement("img");
      img.className = "thumb";
      img.src = item.url;
      img.alt = "";
      const meta = document.createElement("div");
      meta.className = "meta";
      const strong = document.createElement("strong");
      strong.textContent = item.file.name;
      const size = document.createElement("span");
      size.textContent = formatSize(item.file.size);
      meta.append(strong, size);
      const remove = document.createElement("button");
      remove.type = "button";
      remove.setAttribute("aria-label", `Remove ${item.file.name}`);
      remove.textContent = "×";
      remove.addEventListener("click", (e) => {
        e.stopPropagation();
        URL.revokeObjectURL(item.url);
        items = items.filter((_, i) => i !== index);
        renderFiles();
      });
      li.append(img, meta, remove);
      fileList.appendChild(li);
    });
  }

  function addFiles(list) {
    const incoming = [...list].filter(
      (f) =>
        f.type.startsWith("image/") ||
        /\.(jpe?g|png|webp|bmp|tiff?)$/i.test(f.name)
    );
    const key = (f) => `${f.name}:${f.size}:${f.lastModified}`;
    const seen = new Set(items.map((i) => key(i.file)));
    for (const f of incoming) {
      if (!seen.has(key(f))) {
        items.push({ file: f, url: URL.createObjectURL(f) });
        seen.add(key(f));
      }
    }
    renderFiles();
    hideToast();
  }

  dropzone.addEventListener("click", (e) => {
    if (e.target.closest("button")) return;
    fileInput.click();
  });
  dropzone.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      fileInput.click();
    }
  });
  fileInput.addEventListener("change", () => {
    addFiles(fileInput.files || []);
    fileInput.value = "";
  });

  ["dragenter", "dragover"].forEach((evt) => {
    dropzone.addEventListener(evt, (e) => {
      e.preventDefault();
      dropzone.classList.add("is-drag");
    });
  });
  ["dragleave", "drop"].forEach((evt) => {
    dropzone.addEventListener(evt, (e) => {
      e.preventDefault();
      dropzone.classList.remove("is-drag");
    });
  });
  dropzone.addEventListener("drop", (e) => {
    addFiles(e.dataTransfer?.files || []);
  });

  function setBusy(busy) {
    submitBtn.disabled = busy;
    submitBtn.classList.toggle("is-busy", busy);
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    hideToast();

    if (!items.length) {
      showToast("Add at least one image.", true);
      return;
    }
    const keywords = document.getElementById("keywords").value.trim();
    if (!keywords) {
      showToast("Add at least one keyword.", true);
      return;
    }

    const body = new FormData();
    items.forEach((item) => body.append("files", item.file, item.file.name));
    body.append("title", document.getElementById("title").value.trim());
    body.append(
      "description",
      document.getElementById("description").value.trim()
    );
    body.append("keywords", keywords);
    body.append("rating", ratingInput.value);

    setBusy(true);
    try {
      const res = await fetch("/api/process", { method: "POST", body });
      if (!res.ok) {
        let msg = "Something went wrong.";
        try {
          const data = await res.json();
          msg = data.detail || msg;
          if (Array.isArray(data.detail)) {
            msg = data.detail.map((d) => d.msg || d).join(", ");
          }
        } catch (_) {
          msg = (await res.text()) || msg;
        }
        throw new Error(typeof msg === "string" ? msg : "Request failed");
      }

      const blob = await res.blob();
      const cd = res.headers.get("Content-Disposition") || "";
      const match = /filename=\"?([^\";]+)\"?/i.exec(cd);
      const filename = match
        ? match[1]
        : items.length > 1
          ? "droptag-images.zip"
          : "tagged.jpg";

      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);

      showToast(`Done — downloaded ${filename}`);
    } catch (err) {
      showToast(err.message || "Failed to process images.", true);
    } finally {
      setBusy(false);
    }
  });

  window.addEventListener("beforeunload", clearItems);
})();
