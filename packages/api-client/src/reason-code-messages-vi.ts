// SPDX-FileCopyrightText: The metrace Authors
// SPDX-License-Identifier: Apache-2.0
/**
 * Vietnamese message for every machine-readable reason code.
 * Source of truth for the codes: services/api/app/core/reason_codes.py
 * (a unit test fails when a code is missing here).
 */
export const REASON_CODE_MESSAGES_VI: Readonly<Record<string, string>> = {
  // Generic
  VALIDATION_ERROR: "Dữ liệu nhập chưa hợp lệ. Kiểm tra lại các ô đã điền.",
  UNAUTHENTICATED: "Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.",
  FORBIDDEN: "Tài khoản của bạn không có quyền thực hiện thao tác này.",
  NOT_FOUND: "Không tìm thấy dữ liệu được yêu cầu.",
  CONFLICT: "Thao tác không phù hợp với trạng thái hiện tại (ví dụ mẻ chưa nấu xong hoặc đã được xử lý).",
  IDP_UNAVAILABLE: "Không kết nối được dịch vụ đăng nhập. Thử lại sau ít phút.",
  SERVICE_UNAVAILABLE: "Hệ thống tạm thời không khả dụng. Thử lại sau ít phút.",
  METHOD_NOT_ALLOWED: "Thao tác này không được hỗ trợ.",
  UNSUPPORTED_MEDIA_TYPE: "Định dạng dữ liệu gửi lên không được hỗ trợ.",
  RATE_LIMITED: "Thao tác quá nhanh. Đợi vài giây rồi thử lại.",
  INTERNAL_ERROR: "Lỗi hệ thống. Thử lại; nếu vẫn lỗi, báo kèm mã yêu cầu cho quản trị viên.",
  NETWORK_ERROR: "Không kết nối được máy chủ. Kiểm tra mạng rồi thử lại.",

  // P1: nhận hàng (Mẫu 1)
  P1_MISSING_DOCUMENTS: "Chưa đính kèm chứng từ giao hàng. Chụp ảnh hoặc tải PDF phiếu giao hàng trước khi nhận.",
  P1_SUPPLIER_BLOCKED: "Nhà cung cấp đang bị chặn hoặc bị khóa do sự cố chưa đóng. Không được nhận hàng.",
  P1_SUPPLIER_CERT_EXPIRED:
    "Nhà cung cấp không có giấy chứng nhận an toàn thực phẩm còn hiệu lực. Không được nhận hàng.",
  P1_SUPPLIER_CERT_EXPIRING:
    "Giấy chứng nhận an toàn thực phẩm của nhà cung cấp sắp hết hạn. Nhắc nhà cung cấp gia hạn.",
  P1_TEMP_OUT_OF_RANGE: "Nhiệt độ hàng nhận vượt ngưỡng cho phép hoặc chưa được đo. Không nhận dòng hàng này.",

  // P2: nấu (Mẫu 2)
  P2_MISSING_TIMESTAMPS: "Thiếu hoặc sai thời điểm bắt đầu/kết thúc nấu. Không thể hoàn tất mẻ.",
  P2_MISSING_INPUTS: "Mẻ chưa ghi nguyên liệu đầu vào. Ghi lô/mẻ đã dùng trước khi hoàn tất để truy vết được.",
  P2_CORE_TEMP_BELOW_MIN: "Nhiệt độ tâm món ăn thấp hơn mức tối thiểu. Nấu tiếp rồi đo lại.",
  P2_INPUT_LOCKED:
    "Nguyên liệu hoặc mẻ đầu vào (kể cả nguồn phía trước) đang bị khóa do sự cố an toàn thực phẩm. Không được sử dụng.",

  // P3: xuất xe giao hàng
  P3_MISSING_FORM_1: "Có lô nguyên liệu chưa có phiếu nhận hàng (Mẫu 1) đầy đủ chứng từ.",
  P3_MISSING_FORM_2: "Có mẻ trên xe chưa hoàn tất (Mẫu 2).",
  P3_MISSING_FORM_3: "Chưa kiểm tra suất ăn (Mẫu 3) cho mẻ này trên chuyến giao.",
  P3_DISH_NOT_IN_MENU: "Món ăn không có trong thực đơn của khách hàng cho bữa này.",
  P3_HOLD_TIME_EXCEEDED: "Đã quá thời gian giữ món tối đa kể từ khi nấu xong. Không được xuất xe.",
  P3_SAMPLE_MISSING: "Mẻ đủ số suất bắt buộc lưu mẫu nhưng chưa lưu mẫu.",
  P3_UPSTREAM_LOCKED:
    "Có nguyên liệu hoặc mẻ phía trước đang bị khóa do sự cố an toàn thực phẩm. Không được xuất xe.",
  P3_SHIPMENT_HELD: "Chuyến giao đang bị giữ lại, chưa được xuất xe.",
  P3_LINEAGE_TRUNCATED: "Không truy vết trọn vẹn nguồn gốc của mẻ nên hệ thống chặn để đảm bảo an toàn.",
  P3_SHIPMENT_EMPTY: "Chuyến giao chưa có món nào trên xe.",

  // P4: lưu mẫu
  P4_SAMPLE_UNDER_MINIMUM: "Lượng mẫu lưu thấp hơn mức tối thiểu.",
  P4_DISCARD_BEFORE_RETENTION: "Chưa đủ thời gian lưu mẫu nên chưa được hủy.",
  P4_DISCARD_DURING_INCIDENT: "Không được hủy mẫu khi mẻ hoặc ngày phục vụ này liên quan đến sự cố đang mở.",

  // Sự cố (P5: đóng sự cố cần hai người)
  P5_SAME_PERSON: "Người đề nghị đóng sự cố không được tự phê duyệt. Cần một người khác xác nhận.",
  INCIDENT_CLOSED: "Sự cố đã được đóng, không thể thao tác thêm.",
  CLOSE_REQUEST_PENDING: "Đã có đề nghị đóng sự cố đang chờ phê duyệt.",

  // Tệp tải lên
  FILE_TOO_LARGE: "Tệp quá lớn. Chọn tệp nhỏ hơn.",
  FILE_TYPE_NOT_ALLOWED: "Chỉ nhận ảnh JPEG, PNG hoặc tệp PDF.",
  FILE_TYPE_MISMATCH: "Nội dung tệp không khớp với định dạng khai báo. Chọn lại tệp.",
  FILE_EMPTY: "Tệp rỗng. Chọn lại tệp.",
};

export const GENERIC_ERROR_MESSAGE_VI = "Có lỗi xảy ra. Vui lòng thử lại.";

/** Vietnamese message for a reason code; unknown codes get the generic message. */
export function messageForCode(code: string): string {
  return REASON_CODE_MESSAGES_VI[code] ?? GENERIC_ERROR_MESSAGE_VI;
}
