document.addEventListener("DOMContentLoaded", () => {
    const sidebar = document.querySelector(".sidebar");
    const toggle = document.querySelector("[data-sidebar-toggle]");
    const backdrop = document.querySelector("[data-sidebar-backdrop]");

    const closeSidebar = () => {
        sidebar?.classList.remove("show");
        backdrop?.classList.add("d-none");
    };

    toggle?.addEventListener("click", () => {
        sidebar?.classList.toggle("show");
        backdrop?.classList.toggle("d-none");
    });

    backdrop?.addEventListener("click", closeSidebar);

    document.querySelectorAll('[data-role="pricing_select"]').forEach((select) => {
        select.addEventListener("change", () => {
            const form = select.closest("form");
            if (!form) return;
            const option = select.options[select.selectedIndex];
            if (!option.value) return;

            // An order line is sourced from at most one of "Alteration"/"Material" —
            // picking one clears the other so create_line/edit_line's server-side
            // mutual-exclusivity validator never rejects the submission.
            form.querySelectorAll('[data-role="pricing_select"]').forEach((other) => {
                if (other !== select) other.value = "";
            });

            const description = form.querySelector('[data-role="description"]');
            const unitPrice = form.querySelector('[data-role="unit_price"]');
            const vatRate = form.querySelector('[data-role="vat_rate"]');
            if (description) description.value = option.dataset.name || "";
            if (unitPrice) unitPrice.value = option.dataset.price || "";
            if (vatRate) vatRate.value = option.dataset.vat || "";
        });
    });

    document.querySelectorAll("[data-copy-target]").forEach((button) => {
        button.addEventListener("click", async () => {
            const input = document.querySelector(button.dataset.copyTarget);
            if (!input) return;
            try {
                await navigator.clipboard.writeText(input.value);
                const original = button.innerHTML;
                button.innerHTML = '<i class="bi bi-check-lg"></i> Copied';
                setTimeout(() => { button.innerHTML = original; }, 1500);
            } catch {
                input.select();
            }
        });
    });
});
