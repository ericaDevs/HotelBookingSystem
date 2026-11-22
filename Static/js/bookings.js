(function () {
  const form = document.getElementById("booking-form");
  if (!form) return;

  const feedback = document.getElementById("booking-feedback");
  const paymentMethod = document.getElementById("payment-method");
  const mpesaPanel = document.getElementById("panel-mpesa");
  const arrivalPanel = document.getElementById("panel-arrival");
  const mpesaTab = document.getElementById("tab-mpesa");
  const arrivalTab = document.getElementById("tab-arrival");
  const roomSelect = document.getElementById("selected-room");
  const guestPhone = form.elements.namedItem("phone_number");
  const mpesaPhone = document.getElementById("mpesa-phone");

  function showFeedback(message, isError) {
    feedback.textContent = message;
    feedback.classList.remove(
      "hidden",
      "bg-secondary-fixed",
      "text-on-secondary-fixed",
      "bg-tertiary-fixed",
      "text-on-tertiary-fixed",
    );
    feedback.classList.add(isError ? "bg-secondary-fixed" : "bg-tertiary-fixed");
    feedback.classList.add(isError ? "text-on-secondary-fixed" : "text-on-tertiary-fixed");
    feedback.setAttribute("role", isError ? "alert" : "status");
  }

  function clearFeedback() {
    feedback.textContent = "";
    feedback.classList.add("hidden");
    feedback.classList.remove(
      "bg-secondary-fixed",
      "text-on-secondary-fixed",
      "bg-tertiary-fixed",
      "text-on-tertiary-fixed",
    );
    form.querySelectorAll("[data-validation-error]").forEach((input) => {
      input.setCustomValidity("");
      input.removeAttribute("aria-invalid");
      delete input.dataset.validationError;
    });
  }

  function setPaymentMethod(method) {
    const isMpesa = method === "M-Pesa";
    paymentMethod.value = method;
    mpesaPanel.classList.toggle("hidden", !isMpesa);
    mpesaPanel.classList.toggle("flex", isMpesa);
    arrivalPanel.classList.toggle("hidden", isMpesa);
    arrivalPanel.classList.toggle("flex", !isMpesa);
    mpesaTab.setAttribute("aria-pressed", String(isMpesa));
    arrivalTab.setAttribute("aria-pressed", String(!isMpesa));

    const activeTab = isMpesa ? mpesaTab : arrivalTab;
    const activeColor = isMpesa ? "text-tertiary" : "text-secondary";
    const activeStyle = isMpesa
      ? "p-space-md rounded-xl text-left transition-all flex flex-col justify-between gap-space-sm bg-tertiary-fixed/30 text-on-tertiary-fixed shadow-sm"
      : "p-space-md rounded-xl text-left transition-all flex flex-col justify-between gap-space-sm bg-secondary/10 text-secondary shadow-sm";
    const inactiveStyle =
      "p-space-md rounded-xl text-left transition-all flex flex-col justify-between gap-space-sm bg-surface-container-low text-on-surface hover:bg-surface-container shadow-sm";

    [mpesaTab, arrivalTab].forEach((tab) => {
      tab.className = tab === activeTab ? activeStyle : inactiveStyle;
      const radio = tab.firstElementChild?.lastElementChild;
      if (radio) {
        const icon = document.createElement("i");
        icon.dataset.lucide = tab === activeTab ? "disc" : "circle";
        icon.className = tab === activeTab ? `${activeColor} text-xl` : "text-outline text-xl";
        radio.replaceWith(icon);
      }
    });
    if (window.lucide) window.lucide.createIcons();
  }

  mpesaTab.addEventListener("click", () => setPaymentMethod("M-Pesa"));
  arrivalTab.addEventListener("click", () => setPaymentMethod("Pay on Arrival"));

  if (mpesaPhone && guestPhone) {
    guestPhone.addEventListener("input", () => {
      mpesaPhone.value = guestPhone.value;
    });
    mpesaPhone.addEventListener("input", () => {
      guestPhone.value = mpesaPhone.value;
    });
  }

  if (roomSelect) {
    roomSelect.addEventListener("change", () => {
      form.elements.namedItem("room").value = roomSelect.value;
    });
  }

  function collectAndValidate() {
    const data = {
      full_name: form.elements.namedItem("full_name").value.trim().replace(/\s+/g, " "),
      Id_no: form.elements.namedItem("Id_no").value.trim(),
      email: form.elements.namedItem("email").value.trim().toLowerCase(),
      phone_number: form.elements.namedItem("phone_number").value.replace(/[\s()-]/g, ""),
      county_of_origin: form.elements.namedItem("county_of_origin").value.trim().replace(/\s+/g, " "),
      country: form.elements.namedItem("country").value.trim().replace(/\s+/g, " "),
      check_in_date: form.elements.namedItem("check_in_date").value,
      check_out_date: form.elements.namedItem("check_out_date").value,
      room: form.elements.namedItem("room").value,
      payment_method: paymentMethod.value,
    };

    Object.keys(data).forEach((key) => {
      const input = form.elements.namedItem(key);
      if (input) input.value = data[key];
    });

    if (!data.full_name || data.full_name.length > 50) {
      return { field: "full_name", message: "Enter a name of 1 to 50 characters." };
    }
    if (!data.email || !form.elements.namedItem("email").validity.valid) {
      return { field: "email", message: "Enter a valid email address." };
    }
    if (!/^\+?\d{7,15}$/.test(data.phone_number)) {
      return { field: "phone_number", message: "Enter a valid phone number using 7 to 15 digits." };
    }
    if (!data.Id_no || data.Id_no.length > 12) {
      return { field: "Id_no", message: "Enter an ID or passport number of up to 12 characters." };
    }
    if (!data.county_of_origin || data.county_of_origin.length > 50) {
      return { field: "county_of_origin", message: "Enter a county of up to 50 characters." };
    }
    if (!data.country || data.country.length > 50) {
      return { field: "country", message: "Enter a country of up to 50 characters." };
    }
    if (!data.check_in_date || !data.check_out_date) {
      return { field: !data.check_in_date ? "check_in_date" : "check_out_date", message: "Enter both stay dates." };
    }
    if (data.check_out_date <= data.check_in_date) {
      return { field: "check_out_date", message: "Check-out must be after check-in." };
    }
    if (!data.room) {
      return { field: "room", message: "Select an available room." };
    }
    if (!["M-Pesa", "Pay on Arrival"].includes(data.payment_method)) {
      return { field: "payment_method", message: "Select a payment method." };
    }
    return { data };
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    clearFeedback();

    if (!form.reportValidity()) return;

    const validation = collectAndValidate();
    if (validation.message) {
      const field = form.elements.namedItem(validation.field);
      if (field && field.setCustomValidity) {
        field.dataset.validationError = "true";
        field.setAttribute("aria-invalid", "true");
        field.setCustomValidity(validation.message);
        field.reportValidity();
      }
      showFeedback(validation.message, true);
      return;
    }

    const submitButton = event.submitter;
    if (submitButton) submitButton.disabled = true;
    showFeedback("Saving your booking details...", false);

    try {
      const response = await fetch(form.action, {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "Accept": "application/json",
          "Content-Type": "application/json",
          "X-CSRFToken": form.elements.namedItem("csrfmiddlewaretoken").value,
        },
        body: JSON.stringify(validation.data),
      });
      const result = await response.json();

      if (!response.ok) {
        const fieldErrors = result.errors || {};
        const firstError = Object.entries(fieldErrors)[0];
        const message = firstError
          ? `${firstError[1].join(" ")}`
          : "We could not save your booking. Please check the details and try again.";
        const field = firstError && form.elements.namedItem(firstError[0]);
        if (field && field.focus) field.focus();
        showFeedback(message, true);
        return;
      }

      showFeedback(
        `${result.message} Your booking reference is ${result.guest_id}. Payment method selected: ${result.payment_method}.`,
        false,
      );
    } catch (error) {
      showFeedback("Could not reach the booking service. Please try again.", true);
    } finally {
      if (submitButton) submitButton.disabled = false;
    }
  });
})();