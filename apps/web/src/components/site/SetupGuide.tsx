"use client";

import * as Tabs from "@radix-ui/react-tabs";
import { AndroidLogo, AppleLogo, WindowsLogo, Television, ArrowUpRight } from "@phosphor-icons/react";

const platforms = [
  { name: "Android", icon: AndroidLogo, store: "Google Play", url: "https://play.google.com/store/apps/details?id=com.happproxy", steps: ["Установите Happ из Google Play.", "В личном кабинете нажмите «Добавить в Happ» — приложение откроется и подписка появится в списке.", "Выберите сервер и нажмите кнопку подключения. При первом запуске разрешите создание VPN-соединения."] },
  { name: "iPhone / iPad", icon: AppleLogo, store: "App Store", url: "https://apps.apple.com/app/happ-proxy-utility/id6504287215", steps: ["Установите Happ из App Store.", "Нажмите «Добавить в Happ» в личном кабинете, подтвердите открытие приложения.", "Выберите сервер, нажмите подключение и разрешите добавить VPN-конфигурацию."] },
  { name: "Windows", icon: WindowsLogo, store: "сайт Happ", url: "https://www.happ.su/main/ru", steps: ["Скачайте Happ для Windows с официального сайта и установите.", "Скопируйте ссылку подписки из кабинета и вставьте её в Happ: «+» → «Добавить подписку».", "Выберите сервер и подключитесь."] },
  { name: "macOS", icon: AppleLogo, store: "App Store", url: "https://apps.apple.com/app/happ-proxy-utility/id6504287215", steps: ["Установите Happ из App Store.", "Нажмите «Добавить в Happ» в кабинете или вставьте ссылку подписки вручную.", "Выберите сервер и подключитесь."] },
  { name: "Android TV", icon: Television, store: "Google Play", url: "https://play.google.com/store/apps/details?id=com.happproxy", steps: ["Установите Happ из Google Play на телевизоре.", "В Happ выберите добавление подписки по ссылке и введите ссылку из кабинета (или откройте кабинет на телефоне и перепишите).", "Выберите сервер и подключитесь."] },
];

export default function SetupGuide() {
  return (
    <Tabs.Root defaultValue="Android">
      <Tabs.List className="platform-tabs" aria-label="Ваше устройство">
        {platforms.map((p) => <Tabs.Trigger key={p.name} value={p.name} className="platform-tab"><p.icon size={17} aria-hidden />{p.name}</Tabs.Trigger>)}
      </Tabs.List>
      {platforms.map((p) => (
        <Tabs.Content key={p.name} value={p.name}>
          <ol className="guide-steps">{p.steps.map((step, i) => <li key={step}><span className="guide-step-no">0{i + 1}</span><span>{step}</span></li>)}</ol>
          <a href={p.url} target="_blank" rel="noreferrer" className="site-btn site-btn--dark guide-download">Скачать Happ — {p.store}<ArrowUpRight size={18} aria-hidden /></a>
        </Tabs.Content>
      ))}
    </Tabs.Root>
  );
}
