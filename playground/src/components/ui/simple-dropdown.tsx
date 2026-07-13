import {
	Children,
	cloneElement,
	isValidElement,
	type KeyboardEvent,
	type ReactNode,
	useCallback,
	useEffect,
	useRef,
	useState,
} from "react";
import { cn } from "@/utils/cn";

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
	closeDropdown?: () => void;
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

	const handleClose = useCallback(() => {
		setIsAnimating(true);
		setTimeout(() => {
			setIsOpen(false);
			setIsAnimating(false);
		}, 200);
	}, []);

	const handleToggle = useCallback(() => {
		setIsOpen((currentIsOpen) => !currentIsOpen);
	}, []);

	const handleTriggerKeyDown = useCallback(
		(event: KeyboardEvent<HTMLElement>) => {
			if (event.key === "Enter" || event.key === " ") {
				event.preventDefault();
				handleToggle();
			}
		},
		[handleToggle],
	);

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
	}, [isOpen, handleClose]);

	let renderedTrigger: ReactNode = trigger;
	if (isValidElement(trigger)) {
		renderedTrigger = cloneElement(trigger, {
			onClick: handleToggle,
			onKeyDown: handleTriggerKeyDown,
			"aria-expanded": isOpen,
		});
	}

	const renderedChildren = Children.map(children, (child) => {
		if (!isValidElement<DropdownItemProps>(child)) {
			return child;
		}

		return cloneElement(child, { closeDropdown: handleClose });
	});

	return (
		<div className="relative" ref={dropdownRef}>
			{renderedTrigger}
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
				>
					{renderedChildren}
				</div>
			)}
		</div>
	);
}

export function DropdownItem({
	onClick,
	children,
	className,
	closeDropdown,
}: DropdownItemProps) {
	return (
		<button
			type="button"
			className={cn(
				"w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-accent first:rounded-t-md last:rounded-b-md cursor-pointer",
				className,
			)}
			onClick={() => {
				onClick();
				closeDropdown?.();
			}}
		>
			{children}
		</button>
	);
}
