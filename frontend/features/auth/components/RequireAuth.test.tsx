import { screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { renderWithQueryClient } from "@/test-utils/render-with-query";

import { RequireAuth } from "./RequireAuth";

const replaceMock = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: replaceMock }),
}));

const mockUseAuth = vi.fn();
vi.mock("@/hooks/use-auth", () => ({
  useAuth: () => mockUseAuth(),
}));

beforeEach(() => {
  replaceMock.mockReset();
});

describe("RequireAuth", () => {
  it("shows a loading state while auth status is unknown", () => {
    mockUseAuth.mockReturnValue({ user: null, status: "loading" });
    renderWithQueryClient(
      <RequireAuth>
        <p>secret collection</p>
      </RequireAuth>,
    );

    expect(screen.getByRole("status")).toBeInTheDocument();
    expect(screen.queryByText("secret collection")).not.toBeInTheDocument();
  });

  it("redirects guests to /login with a next param and renders nothing", () => {
    mockUseAuth.mockReturnValue({ user: null, status: "guest" });
    renderWithQueryClient(
      <RequireAuth>
        <p>secret collection</p>
      </RequireAuth>,
    );

    expect(replaceMock).toHaveBeenCalledWith(expect.stringContaining("/login?next="));
    expect(screen.queryByText("secret collection")).not.toBeInTheDocument();
  });

  it("renders children once authenticated", () => {
    mockUseAuth.mockReturnValue({
      user: { id: "u1", email: "a@b.com", display_name: "A", avatar_url: null, created_at: "2026-01-01" },
      status: "authenticated",
    });
    renderWithQueryClient(
      <RequireAuth>
        <p>secret collection</p>
      </RequireAuth>,
    );

    expect(screen.getByText("secret collection")).toBeInTheDocument();
    expect(replaceMock).not.toHaveBeenCalled();
  });
});
