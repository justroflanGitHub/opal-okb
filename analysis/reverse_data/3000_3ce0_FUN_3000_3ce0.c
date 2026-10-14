
/* WARNING: Control flow encountered bad instruction data */
/* WARNING: Instruction at (ram,0x00033d1f) overlaps instruction at (ram,0x00033d1e)
    */

void __stdcall16far FUN_3000_3ce0(void)

{
  int iVar1;
  undefined2 uVar2;
  code *pcVar3;
  int *piVar4;
  uint *puVar5;
  bool bVar6;
  int *piVar7;
  uint in_CX;
  int *in_BX;
  uint unaff_BP;
  uint uVar8;
  int unaff_SI;
  int unaff_DI;
  undefined2 unaff_ES;
  undefined2 unaff_CS;
  undefined2 uVar9;
  undefined2 unaff_SS;
  undefined2 unaff_DS;
  undefined1 uVar10;
  
  *(int *)(unaff_DI + 0x42) = *(int *)(unaff_DI + 0x42) + unaff_SI;
  do {
    uVar9 = unaff_CS;
    if (in_BX[1] == 0) {
      piVar4 = (int *)*(undefined4 *)(unaff_BP + 0x16);
      if (*piVar4 != 0 || ((int *)piVar4)[1] != 0) {
        pcVar3 = (code *)swi(0x35);
        (*pcVar3)();
        uVar8 = unaff_BP ^ in_CX;
        pcVar3 = (code *)swi(0x34);
        (*pcVar3)();
        pcVar3 = (code *)swi(0x3c);
        (*pcVar3)();
        pcVar3 = (code *)swi(0x35);
        (*pcVar3)();
        *(undefined2 *)((uVar8 ^ in_CX) - 0x33) = unaff_DS;
                    /* WARNING: Bad instruction - Truncating control flow here */
        halt_baddata();
      }
      pcVar3 = (code *)swi(0x35);
      (*pcVar3)();
      unaff_BP = unaff_BP ^ in_CX;
      *(undefined2 *)(unaff_BP - 0x33) = unaff_DS;
      pcVar3 = (code *)swi(0x3d);
      (*pcVar3)();
    }
    do {
      iVar1 = *(int *)((int)*(undefined4 *)(unaff_BP - 0x16) + 2);
      *(int *)0x5e70 = iVar1;
      uVar2 = *(undefined2 *)(unaff_BP + 0xc);
      *(int *)(unaff_BP - 4) =
           (iVar1 * *(int *)*(undefined4 *)(unaff_BP + 6) + *(int *)(unaff_BP + 10)) -
           *(int *)(unaff_BP - 0x12);
      *(undefined2 *)(unaff_BP - 2) = uVar2;
      uVar10 = (undefined1)(in_CX >> 8);
      iVar1 = *(int *)0x5e72;
      unaff_CS = 0x2e73;
      func_0x0002f5ce(uVar9,0xefa,*(undefined2 *)(unaff_BP - 4),*(undefined2 *)(unaff_BP - 2),
                      *(undefined2 *)0x5e70,iVar1 + -1,(iVar1 >> 0xf) - (uint)(iVar1 == 0),
                      *(int *)0x5e72 * 8 + 0x28,0x4dfd);
      puVar5 = (uint *)*(undefined4 *)(unaff_BP + 6);
      uVar8 = *puVar5;
      *puVar5 = *puVar5 + 1;
      ((uint *)puVar5)[1] = ((uint *)puVar5)[1] + (uint)(0xfffe < uVar8);
      piVar4 = (int *)0x5e72;
      iVar1 = *piVar4;
      *piVar4 = *piVar4 + 1;
      if ((SCARRY2(iVar1,1)) || (*(int *)(unaff_BP - 0x18) < (int)*(uint *)0x5e72)) {
        return;
      }
      in_CX = CONCAT11(uVar10,3);
      uVar10 = (*(uint *)0x5e72 & 0x1fff) == 0;
      pcVar3 = (code *)swi(0x3c);
      (*pcVar3)();
      pcVar3 = (code *)swi(0x3c);
      (*pcVar3)();
      pcVar3 = (code *)swi(0x39);
      (*pcVar3)();
      if (!(bool)uVar10) {
        pcVar3 = (code *)swi(0x3d);
        (*pcVar3)();
        piVar4 = (int *)*(undefined4 *)(unaff_BP + 0x1e);
        bVar6 = ((int *)piVar4)[1] == 0;
        uVar10 = *piVar4 == 0 && bVar6;
        if (*piVar4 == 0 && bVar6) {
          pcVar3 = (code *)swi(0x39);
          (*pcVar3)();
          pcVar3 = (code *)swi(0x38);
          (*pcVar3)();
          if ((bool)uVar10) {
            pcVar3 = (code *)swi(0x34);
            (*pcVar3)();
          }
          else {
            pcVar3 = (code *)swi(0x39);
            (*pcVar3)();
            if (!(bool)uVar10) {
              pcVar3 = (code *)swi(0x3d);
              (*pcVar3)();
              goto LAB_3000_3dd7;
            }
          }
          unaff_BP = unaff_BP ^ in_CX;
          pcVar3 = (code *)swi(0x3c);
          (*pcVar3)();
          pcVar3 = (code *)swi(0x35);
          (*pcVar3)();
          pcVar3 = (code *)swi(0x3d);
          (*pcVar3)();
        }
        else {
LAB_3000_3dd7:
          in_CX = CONCAT11((char)(in_CX >> 8),3);
          pcVar3 = (code *)swi(0x3c);
          (*pcVar3)();
          pcVar3 = (code *)swi(0x35);
          piVar7 = (int *)(*pcVar3)();
          iVar1 = *piVar7;
          pcVar3 = (code *)swi(0x3d);
          (*pcVar3)();
          pcVar3 = (code *)swi(0x3c);
          (*pcVar3)();
          pcVar3 = (code *)swi(0x35);
          (*pcVar3)();
          *(undefined2 *)(unaff_BP - 0x33) = unaff_DS;
          piVar4 = (int *)(iVar1 + 3);
          *piVar4 = *piVar4 + iVar1;
        }
      }
      piVar4 = (int *)*(undefined4 *)(unaff_BP + 0x1e);
      unaff_ES = (undefined2)((ulong)piVar4 >> 0x10);
      in_BX = (int *)piVar4;
      uVar9 = unaff_CS;
    } while (*piVar4 != 1);
  } while( true );
}

