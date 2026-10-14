
void __stdcall16far FUN_1000_d3bd(void)

{
  undefined2 uVar1;
  code *pcVar2;
  undefined1 uVar3;
  char cVar4;
  uint uVar5;
  int iVar6;
  undefined2 extraout_DX;
  uint unaff_BP;
  undefined2 unaff_SS;
  undefined2 unaff_DS;
  
  uVar1 = *(undefined2 *)(unaff_BP + 0xc);
  *(int *)(unaff_BP - 0x26) = *(int *)(unaff_BP + 10) + 4;
  *(undefined2 *)(unaff_BP - 0x24) = uVar1;
  uVar1 = *(undefined2 *)(unaff_BP + 0x18);
  *(int *)(unaff_BP - 0x2a) = *(int *)(unaff_BP + 0x16) + 8;
  *(undefined2 *)(unaff_BP - 0x28) = uVar1;
  do {
    iVar6 = *(int *)(unaff_BP - 0x1e);
    *(int *)0x4dc0 = *(int *)0x4dc0 + iVar6;
    pcVar2 = (code *)swi(0x35);
    uVar3 = (*pcVar2)();
    out(extraout_DX,uVar3);
    pcVar2 = (code *)swi(0x3c);
    (*pcVar2)();
    pcVar2 = (code *)swi(0x39);
    uVar5 = (*pcVar2)();
    cVar4 = (char)((uint)iVar6 >> 8);
    iVar6 = CONCAT11(cVar4,(char)iVar6 + cVar4 + (uVar5 < 0x5ec4));
    pcVar2 = (code *)swi(0x39);
    cVar4 = (*pcVar2)();
    out(0xcd,cVar4 + -0x33);
    cVar4 = (char)(cVar4 + -0x33) == (char)iVar6;
    pcVar2 = (code *)swi(0x35);
    (*pcVar2)();
    pcVar2 = (code *)swi(0x3a);
    (*pcVar2)();
    unaff_BP = *(uint *)(unaff_BP >> 8 | unaff_BP << 8);
    pcVar2 = (code *)swi(0x35);
    (*pcVar2)();
  } while (iVar6 != 1 && cVar4 == '\0');
  pcVar2 = (code *)swi(0x34);
  (*pcVar2)();
  return;
}

