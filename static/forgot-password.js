// SPDX-License-Identifier: Apache-2.0
// Copyright (c) 2026 Helpmefindthejob contributors
//
// AUDIT-26: minimal /forgot-password page handler.
//
// The /forgot-password route serves a dedicated ~8 KB page instead
// of the 103 KB SPA shell. This script is the page's only JS: it
// captures the form submit, POSTs JSON to /api/auth/forgot-password,
// and renders the localized response in the live-region paragraph.
// All user-visible strings are read from data-* attributes on the
// form element so the same script powers both the EN and DE pages.

(function () {
  "use strict";

  var form = document.getElementById("forgotPasswordForm");
  var message = document.getElementById("forgotPasswordMessage");
  var emailInput = document.getElementById("forgotEmail");
  if (!form || !message || !emailInput) {
    return;
  }

  function setMessage(text) {
    while (message.firstChild) {
      message.removeChild(message.firstChild);
    }
    message.appendChild(document.createTextNode(text));
  }

  form.addEventListener("submit", function (event) {
    event.preventDefault();
    setMessage("");
    var email = (emailInput.value || "").trim();
    if (!email) {
      setMessage(form.dataset.errEmpty || "Please enter your email.");
      emailInput.focus();
      return;
    }
    var submitBtn = form.querySelector('button[type="submit"]');
    if (submitBtn) {
      submitBtn.disabled = true;
    }
    fetch("/api/auth/forgot-password", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: email })
    }).then(function (response) {
      if (response.status === 429) {
        setMessage(form.dataset.errRateLimited || "Too many reset requests. Try again later.");
      } else if (!response.ok) {
        setMessage(form.dataset.errNetwork || "Could not send the reset request. Please try again.");
      } else {
        setMessage(form.dataset.msgSent || "If a matching account exists, a reset link has been sent.");
        form.reset();
      }
    }).catch(function () {
      setMessage(form.dataset.errNetwork || "Could not send the reset request. Please try again.");
    }).then(function () {
      if (submitBtn) {
        submitBtn.disabled = false;
      }
    });
  });
})();
