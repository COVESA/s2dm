import type { LedgerRootState } from "@ledger-ui/state/types";
import { useDispatch, useSelector } from "react-redux";

export const useLedgerSelector = useSelector.withTypes<LedgerRootState>();
export const useLedgerDispatch = useDispatch;
