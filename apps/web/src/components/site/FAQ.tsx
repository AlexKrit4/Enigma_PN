"use client";

import * as Accordion from "@radix-ui/react-accordion";
import { Plus } from "@phosphor-icons/react";

const questions = [
  ["Что такое обход белых списков?", "В некоторых сетях доступны только разрешённые провайдером сайты. Для таких случаев в подписке есть отдельное подключение «Обход». Попробуйте его, если обычный сервер не подключается."],
  ["Как получить 1 день бесплатно?", "Создайте аккаунт и подтвердите почту кодом из письма. После подтверждения пробный период включится автоматически: 1 день, 5 устройств и безлимитный трафик. Карта не нужна."],
  ["На каких устройствах это работает?", "На Android, iPhone, iPad, Windows, macOS и Android TV через бесплатное приложение Happ. Одна подписка включает 5 устройств — например, телефон, ноутбук и телевизор."],
  ["Что делать, если нужно больше 5 устройств?", "Добавьте устройства при оформлении или позже в личном кабинете. Каждое дополнительное устройство стоит 50 ₽ в месяц. Максимум — 50 устройств."],
  ["Как продлить подписку?", "В личном кабинете выберите срок и оплатите через ЮMoney. Новый срок прибавится к текущему. Ссылку в Happ менять не нужно."],
  ["Будет работать в моей сети?", "Это зависит от ограничений вашего провайдера. Именно поэтому сначала можно проверить подключение бесплатно в течение 1 дня. Если возникают сложности, поможем в поддержке."],
];

export default function FAQ() {
  return (
    <Accordion.Root type="single" collapsible className="site-accordion">
      {questions.map(([question, answer], index) => (
        <Accordion.Item key={question} value={String(index)} className="site-accordion-item">
          <Accordion.Header>
            <Accordion.Trigger className="site-accordion-trigger">{question}<Plus size={20} aria-hidden /></Accordion.Trigger>
          </Accordion.Header>
          <Accordion.Content className="site-accordion-content"><div className="site-accordion-body">{answer}</div></Accordion.Content>
        </Accordion.Item>
      ))}
    </Accordion.Root>
  );
}
