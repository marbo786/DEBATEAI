import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import SummaryCard from "../SummaryCard";
import type { SummaryPayload, DebateState } from "../../types";

const summary: SummaryPayload = {
  topic: "Test",
  winner: "pro",
  final_belief: 0.6,
  final_pro_pct: 60,
  final_con_pct: 40,
  turning_point_round: 2,
  total_rounds: 6,
};

const state: DebateState = {
  topic: "Test",
  user_side: "auto",
  round: 3,
  max_rounds: 6,
  belief: 0.6,
  pro_claims: [],
  con_claims: [],
  history: [],
};

describe("SummaryCard overrides", () => {
  it("keeps override preview and disables buttons while request is pending, then clears preview on success", async () => {
    let resolveOverride: (value: boolean) => void;
    const onOverride = vi.fn(
      () =>
        new Promise<boolean>((resolve) => {
          resolveOverride = resolve;
        })
    );

    render(<SummaryCard summary={summary} state={state} onOverride={onOverride} />);
    const proButton = screen.getByRole("button", { name: /Pro Believer/i });

    await userEvent.click(proButton);

    expect(onOverride).toHaveBeenCalledWith(1);
    expect(proButton).toBeDisabled();
    expect(screen.getByText("Pro 100%")).toBeInTheDocument();

    resolveOverride!(true);

    await waitFor(() => expect(proButton).not.toBeDisabled());
  });

  it("rolls back local preview when override request fails", async () => {
    const onOverride = vi.fn().mockResolvedValue(false) as (value: number | null) => Promise<boolean>;

    render(<SummaryCard summary={summary} state={state} onOverride={onOverride} />);

    await userEvent.click(screen.getByRole("button", { name: /Con Believer/i }));

    await waitFor(() => {
      expect(screen.getByText("Pro 60%")).toBeInTheDocument();
      expect(screen.getByText("Con 40%")).toBeInTheDocument();
    });
  });
});
