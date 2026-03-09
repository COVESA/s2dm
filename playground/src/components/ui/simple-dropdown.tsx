import type { ReactNode } from "react";
import { useEffect, useRef, useState } from "react";
import { cn } from "@/lib/utils";

type DropdownProps = {
	trigger: ReactNode;
	children: ReactNode;
	align?: "start" | "end";
	className?: string;
};

type DropdownItemProps = {
	onClick: () => void;
	children: ReactNode;
	className?: string;
};

export function Dropdown({
	trigger,
	children,
	align = "end",
	className,
}: DropdownProps) {
	const [isOpen, setIsOpen] = useState(false);
	const [isAnimating, setIsAnimating] = useState(false);
	const dropdownRef = useRef<HTMLDivElement>(null);

	useEffect(() => {
		const handleClickOutside = (event: MouseEvent) => {
			if (
				dropdownRef.current &&
				!dropdownRef.current.contains(event.target as Node)
			) {
				handleClose();
			}
		};

		if (isOpen) {
			document.addEventListener("mousedown", handleClickOutside);
		}

		return () => {
			document.removeEventListener("mousedown", handleClickOutside);
		};
	}, [isOpen]);

	const handleClose = () => {
		setIsAnimating(true);
		setTimeout(() => {
			setIsOpen(false);
			setIsAnimating(false);
		}, 200);
	};

	return (
		<div className="relative" ref={dropdownRef}>
			<div onClick={() => setIsOpen(!isOpen)}>{trigger}</div>
			{isOpen && (
				<div
					className={cn(
						"absolute top-full mt-1 bg-popover border rounded-md shadow-md z-50 min-w-[160px]",
						isAnimating
							? "animate-out fade-out-0 zoom-out-95 slide-out-to-top-2 duration-200"
							: "animate-in fade-in-0 zoom-in-95 slide-in-from-top-2 duration-200",
						align === "end" ? "right-0" : "left-0",
						className,
					)}
					onClick={() => handleClose()}
				>
					{children}
				</div>
			)}
		</div>
	);
}

export function DropdownItem({
	onClick,
	children,
	className,
}: DropdownItemProps) {
	return (
		<button
			className={cn(
				"w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-accent first:rounded-t-md last:rounded-b-md cursor-pointer",
				className,
			)}
			onClick={onClick}
		>
			{children}
		</button>
	);
}
