import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import SummaryCard from "../SummaryCard";

const summary = {
  topic: "Test",
  winner: "pro",
  final_pro_pct: 60,
  final_con_pct: 40,
};

describe("SummaryCard overrides", () => {
  it("keeps override preview and disables buttons while request is pending, then clears preview on success", async () => {
    let resolveOverride;
    const onOverride = vi.fn(
      () =>
        new Promise((resolve) => {
          resolveOverride = resolve;
        })
    );

    render(<SummaryCard summary={summary} state={{ topic: "Test" }} onOverride={onOverride} />);
    const proButton = screen.getByRole("button", { name: "Pro" });

    await userEvent.click(proButton);

    expect(onOverride).toHaveBeenCalledWith(1);
    expect(proButton).toBeDisabled();
    expect(screen.getByText("Pro 100%")).toBeInTheDocument();

    resolveOverride(true);

    await waitFor(() => expect(proButton).not.toBeDisabled());
  });

  it("rolls back local preview when override request fails", async () => {
    const onOverride = vi.fn().mockResolvedValue(false);

    render(<SummaryCard summary={summary} state={{ topic: "Test" }} onOverride={onOverride} />);

    await userEvent.click(screen.getByRole("button", { name: "Con" }));

    await waitFor(() => {
      expect(screen.getByText("Pro 60%")).toBeInTheDocument();
      expect(screen.getByText("Con 40%")).toBeInTheDocument();
    });
  });
});
