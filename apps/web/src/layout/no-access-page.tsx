// SPDX-FileCopyrightText: The metrace Authors
// SPDX-License-Identifier: Apache-2.0
import { logout } from "../auth/keycloak-session";
import { Button } from "../components/ui-primitives";

/** Signed in, but the account carries none of the metrace roles. */
export function NoAccessPage() {
  return (
    <main className="mx-auto mt-24 max-w-xl space-y-4 rounded-xl bg-white p-8 text-center shadow-sm ring-1 ring-slate-200">
      <h1 className="text-3xl font-bold">Tài khoản chưa được cấp quyền</h1>
      <p className="text-lg text-slate-700">
        Tài khoản này chưa có vai trò nào trong hệ thống. Liên hệ quản trị viên để được cấp quyền, sau đó đăng nhập lại.
      </p>
      <Button onClick={() => void logout()}>Đăng xuất</Button>
    </main>
  );
}
