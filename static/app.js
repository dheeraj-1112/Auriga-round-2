document.addEventListener("DOMContentLoaded", function () {
    var copyBtn = document.getElementById("copy-settlement-btn");
    if (!copyBtn) return;

    copyBtn.addEventListener("click", function () {
        var list = document.getElementById("settlement-list");
        if (!list) return;
        var lines = Array.prototype.map.call(list.querySelectorAll("li"), function (li) {
            return li.textContent.trim();
        });
        var text = lines.join("\n");

        navigator.clipboard.writeText(text).then(function () {
            var original = copyBtn.textContent;
            copyBtn.textContent = "Copied!";
            setTimeout(function () {
                copyBtn.textContent = original;
            }, 1500);
        }).catch(function () {
            alert(text); // fallback if clipboard API unavailable
        });
    });
});
