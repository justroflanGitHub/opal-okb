
void __cdecl16far FUN_15f4_0069(void)

{
  byte *pbVar1;
  int *piVar2;
  byte bVar3;
  code *pcVar4;
  char cVar5;
  undefined2 uVar6;
  byte bVar7;
  char in_CH;
  int in_BX;
  int unaff_SI;
  int unaff_DI;
  int unaff_ES;
  undefined2 unaff_DS;
  
  pcVar4 = (code *)swi(0x21);
  (*pcVar4)();
  if (unaff_ES != in_BX) {
    pcVar4 = (code *)swi(0x90);
    (*pcVar4)();
    return;
  }
  pcVar4 = (code *)swi(0x21);
  (*pcVar4)();
  pcVar4 = (code *)swi(0x21);
  uVar6 = (*pcVar4)();
  cVar5 = (char)uVar6;
  *(char *)(in_BX + unaff_SI) = *(char *)(in_BX + unaff_SI) + cVar5;
  *(char *)(in_BX + unaff_SI) = *(char *)(in_BX + unaff_SI) + cVar5;
  pbVar1 = (byte *)(in_BX + 0x66);
  bVar3 = *pbVar1;
  bVar7 = (byte)((uint)uVar6 >> 8);
  *pbVar1 = *pbVar1 + bVar7;
  if (CARRY1(bVar3,bVar7) || *pbVar1 == 0) {
    *(char *)(in_BX + -0x71ff) = *(char *)(in_BX + -0x71ff) + in_CH;
    piVar2 = (int *)(in_BX + unaff_DI + 1 + -0x2dfa);
    *piVar2 = *piVar2 + unaff_DI + 1;
    do {
                    /* WARNING: Do nothing block with infinite loop */
    } while( true );
  }
  *(char *)(in_BX + unaff_SI) = *(char *)(in_BX + unaff_SI) + cVar5 + CARRY1(bVar3,bVar7);
  return;
}

