(function () {
  function initializePublicContactForm() {
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
      if (data.phone_number.length > 15 || !/^\+?[0-9]{7,15}$/.test(data.phone_number)) {
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
  }

  function initializeStaffContacts() {
    const module = document.getElementById("staff-contacts-module");
    if (!module) return;

    const search = document.getElementById("staff-contact-search");
    const tableBody = document.getElementById("staff-contact-rows");
    const count = document.getElementById("staff-contact-count");
    const empty = document.getElementById("staff-contact-empty");
    const noRecords = document.getElementById("staff-contact-no-records");
    const actionFeedback = document.getElementById("contact-action-feedback");
    const viewDialog = document.getElementById("contact-view-modal");
    const replyDialog = document.getElementById("contact-reply-modal");
    const deleteDialog = document.getElementById("contact-delete-modal");
    const replyForm = document.getElementById("contact-reply-form");
    const deleteForm = document.getElementById("contact-delete-form");
    let deletingRow = null;

    function showActionFeedback(message, isError) {
      actionFeedback.textContent = message;
      actionFeedback.classList.toggle("error", isError);
      actionFeedback.classList.remove("hidden");
    }

    function updateContactMetrics() {
      const rows = Array.from(tableBody.querySelectorAll(".staff-contact-row"));
      const counts = { total: rows.length, rooms: 0, events: 0, other: 0 };
      rows.forEach((row) => {
        if (row.dataset.inquiryType === "rooms") counts.rooms += 1;
        else if (row.dataset.inquiryType === "conferences") counts.events += 1;
        else counts.other += 1;
      });
      Object.entries(counts).forEach(([name, value]) => {
        const metric = module.querySelector(`[data-contact-metric="${name}"]`);
        if (metric) metric.textContent = String(value);
      });
    }

    function renderRows() {
      const rows = Array.from(tableBody.querySelectorAll(".staff-contact-row"));
      const term = search.value.trim().toLowerCase();
      let shown = 0;
      rows.forEach((row) => {
        const matches = row.dataset.search.includes(term);
        row.hidden = !matches;
        if (matches) shown += 1;
      });
      if (empty) empty.hidden = shown > 0 || rows.length === 0;
      if (noRecords) noRecords.hidden = rows.length > 0;
      count.textContent = `Showing ${shown} of ${rows.length} contact submissions`;
      updateContactMetrics();
    }

    function setFieldValue(fieldId, value) {
      document.getElementById(fieldId).value = value || "";
    }

    module.addEventListener("click", (event) => {
      const button = event.target.closest("[data-contact-action]");
      if (!button) return;

      const row = button.closest(".staff-contact-row");
      if (!row) return;

      if (button.dataset.contactAction === "view") {
        setFieldValue("view-contact-name", button.dataset.contactName);
        setFieldValue("view-contact-email", button.dataset.contactEmail);
        setFieldValue("view-contact-phone", button.dataset.contactPhone);
        setFieldValue("view-contact-type", button.dataset.contactType);
        setFieldValue("view-contact-subject", button.dataset.contactSubject);
        setFieldValue("view-contact-message", button.dataset.contactMessage);
        viewDialog.showModal();
      } else if (button.dataset.contactAction === "reply") {
        setFieldValue("reply-contact-email", button.dataset.contactEmail);
        const subject = button.dataset.contactSubject || "";
        setFieldValue("reply-contact-subject", subject.toLowerCase().startsWith("re:")
          ? subject
          : `Re: ${subject}`);
        setFieldValue("reply-contact-message", "");
        document.getElementById("contact-reply-feedback").textContent = "";
        replyForm.dataset.contactName = button.dataset.contactName || "";
        replyDialog.showModal();
      } else if (button.dataset.contactAction === "delete") {
        deletingRow = row;
        document.getElementById("delete-contact-id").value = row.dataset.contactId;
        document.getElementById("delete-contact-summary").textContent =
          `Delete the contact submission from ${button.dataset.contactName} (${button.dataset.contactEmail})?`;
        document.getElementById("contact-delete-feedback").textContent = "";
        deleteDialog.showModal();
      }

      if (window.lucide) window.lucide.createIcons();
    });

    document.querySelectorAll(
      "#contact-view-modal [data-modal-close], #contact-reply-modal [data-modal-close], #contact-delete-modal [data-modal-close]",
    ).forEach((button) => {
      button.addEventListener("click", () => button.closest("dialog").close());
    });

    document.querySelectorAll("#contact-view-modal, #contact-reply-modal, #contact-delete-modal").forEach((dialog) => {
      dialog.addEventListener("click", (event) => {
        if (event.target === dialog) dialog.close();
      });
    });

    replyForm.addEventListener("submit", (event) => {
      event.preventDefault();
      if (!replyForm.reportValidity()) return;
      const recipient = document.getElementById("reply-contact-email").value;
      const subject = document.getElementById("reply-contact-subject").value.trim();
      const message = document.getElementById("reply-contact-message").value.trim();
      const mailto = `mailto:${encodeURIComponent(recipient)}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(message)}`;
      document.getElementById("contact-reply-feedback").textContent =
        "Opening your email application with the reply draft.";
      window.location.href = mailto;
    });

    deleteForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      if (!deletingRow) return;

      const submitButton = deleteForm.querySelector('[type="submit"]');
      submitButton.disabled = true;
      try {
        const response = await fetch(deleteForm.action, {
          method: "POST",
          credentials: "same-origin",
          headers: {
            Accept: "application/json",
            "Content-Type": "application/json",
            "X-CSRFToken": deleteForm.elements.namedItem("csrfmiddlewaretoken").value,
          },
          body: JSON.stringify({
            action: "delete",
            contact_id: deleteForm.elements.namedItem("contact_id").value,
          }),
        });
        const result = await response.json();
        if (!response.ok) {
          document.getElementById("contact-delete-feedback").textContent =
            result.message || "The contact submission could not be deleted.";
          return;
        }

        deletingRow.remove();
        deletingRow = null;
        deleteDialog.close();
        renderRows();
        showActionFeedback(result.message, false);
      } catch (error) {
        document.getElementById("contact-delete-feedback").textContent =
          "Could not reach the contact service. Please try again.";
      } finally {
        submitButton.disabled = false;
      }
    });

    search.addEventListener("input", renderRows);
    renderRows();
  }

  initializePublicContactForm();
  initializeStaffContacts();
})();
