(function () {
  const form = document.getElementById("contactForm");
  if (!form) return;

  const feedback = document.getElementById("contactFormFeedback");
  const toast = document.getElementById("formSuccessToast");
  const submitButton = document.getElementById("submitBtn");
  const originalButtonContent = submitButton.innerHTML;

  function showError(message) {
    feedback.textContent = message;
    feedback.classList.remove("hidden");
    feedback.setAttribute("role", "alert");
    toast.classList.add("hidden");
  }

  function clearError() {
    feedback.textContent = "";
    feedback.classList.add("hidden");
    form.querySelectorAll("[data-validation-error]").forEach((input) => {
      input.setCustomValidity("");
      input.removeAttribute("aria-invalid");
      delete input.dataset.validationError;
    });
  }

  function collectAndValidate() {
    const data = {
      full_name: form.elements.namedItem("full_name").value.trim().replace(/\s+/g, " "),
      email: form.elements.namedItem("email").value.trim().toLowerCase(),
      phone_number: form.elements.namedItem("phone_number").value.replace(/[\s().-]/g, ""),
      inquery_type: form.elements.namedItem("inquery_type").value.trim(),
      subject: form.elements.namedItem("subject").value.trim().replace(/\s+/g, " "),
      message: form.elements.namedItem("message").value.trim(),
    };

    Object.keys(data).forEach((key) => {
      form.elements.namedItem(key).value = data[key];
    });

    if (!data.full_name || data.full_name.length > 50) {
      return { field: "full_name", message: "Enter a name of 1 to 50 characters." };
    }
    if (!data.email || !form.elements.namedItem("email").validity.valid) {
      return { field: "email", message: "Enter a valid email address." };
    }
    if (
      data.phone_number.length > 15 ||
      !/^\+?[0-9]{7,15}$/.test(data.phone_number)
    ) {
      return { field: "phone_number", message: "Enter a valid phone number." };
    }
    if (!data.inquery_type || data.inquery_type.length > 50) {
      return { field: "inquery_type", message: "Select a valid inquiry type." };
    }
    if (!data.subject || data.subject.length > 100) {
      return { field: "subject", message: "Enter a subject of 1 to 100 characters." };
    }
    if (!data.message) {
      return { field: "message", message: "Enter a message." };
    }

    return { data };
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    clearError();
    if (!form.reportValidity()) return;

    const validation = collectAndValidate();
    if (validation.message) {
      const field = form.elements.namedItem(validation.field);
      field.dataset.validationError = "true";
      field.setAttribute("aria-invalid", "true");
      field.setCustomValidity(validation.message);
      field.reportValidity();
      showError(validation.message);
      return;
    }

    submitButton.disabled = true;
    submitButton.textContent = "Sending...";
    try {
      const response = await fetch(form.action, {
        method: "POST",
        credentials: "same-origin",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
          "X-CSRFToken": form.elements.namedItem("csrfmiddlewaretoken").value,
        },
        body: JSON.stringify(validation.data),
      });
      const result = await response.json();

      if (!response.ok) {
        const firstError = Object.entries(result.errors || {})[0];
        const message = firstError
          ? firstError[1].join(" ")
          : "We could not send your message. Check the details and try again.";
        const field = firstError && form.elements.namedItem(firstError[0]);
        if (field && field.focus) field.focus();
        showError(message);
        return;
      }

      feedback.classList.add("hidden");
      toast.classList.remove("hidden");
      form.reset();
    } catch (error) {
      showError("Could not reach the contact service. Please try again.");
    } finally {
      submitButton.disabled = false;
      submitButton.innerHTML = originalButtonContent;
      if (window.lucide) window.lucide.createIcons();
    }
  });
})();