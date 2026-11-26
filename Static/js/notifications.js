document.querySelectorAll("[data-toast]").forEach((toast) => {
  const dismiss = () => toast.remove();
  const closeButton = toast.querySelector(".portal-toast-close");
  if (closeButton) closeButton.addEventListener("click", dismiss);
  window.setTimeout(dismiss, 6000);
});
