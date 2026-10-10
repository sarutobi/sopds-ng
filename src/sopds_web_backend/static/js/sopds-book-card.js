/*
 * Раскрытие/свёртывание аннотации в карточке книги.
 * Делегирование на document — переживает HTMX-замену #list-content.
 * Короткие аннотации (не переполняют clamp) скрывают кнопку при загрузке.
 */
document.addEventListener("click", function (e) {
  const toggle = e.target.closest(".sopds-annotation-toggle");
  if (!toggle) return;
  e.preventDefault();
  const block = toggle.closest(".sopds-annotation");
  const expanded = block.classList.toggle("expanded");
  toggle.textContent = expanded
    ? toggle.dataset.labelLess
    : toggle.dataset.labelMore;
});

function initAnnotationToggles() {
  document.querySelectorAll(".sopds-annotation").forEach(function (block) {
    const text = block.querySelector(".sopds-annotation-text");
    const toggle = block.querySelector(".sopds-annotation-toggle");
    if (!text || !toggle) return;
    // Кнопка не нужна, если аннотация целиком помещается в clamp
    if (text.scrollHeight <= text.clientHeight + 1) {
      toggle.style.display = "none";
    } else {
      toggle.style.display = "";
    }
  });
}

document.addEventListener("DOMContentLoaded", initAnnotationToggles);
document.addEventListener("htmx:afterSwap", initAnnotationToggles);
